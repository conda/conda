#!/usr/bin/env python
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Accumulate jlap patches in a single separate file, to avoid overhead of
rewriting large file each time.
"""

from __future__ import annotations

import json
import logging
import time
from collections import UserDict
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from jsonpatch import JsonPatchException
from jsonpointer import JsonPointerException

log = logging.getLogger(__name__)

SHOW_PATCH_STEPS = False


@contextmanager
def timeme(message):
    begin = time.monotonic_ns()
    yield
    end = time.monotonic_ns()
    log.debug("%sTook %0.02fs", message, (end - begin) / 1e9)


def dumps(obj):
    """
    Desired dumps() parameters for this module.
    """
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, check_circular=False)


class JSONLoader:
    """
    Load JSON on demand.
    """

    backing_path: Path
    _backing: Any

    def __init__(self, backing_path):
        self.backing_path = backing_path
        self._backing = object  # sentinel

    def __call__(self) -> Any:
        if self._backing is object:
            with timeme(f"Lazy load {self.backing_path.name} "):
                self._backing = json.loads(self.backing_path.read_text())
        return self._backing


class LazyCOWDict(UserDict):
    """
    Support copy-on-write dictionary access, reading only when necessary.

    Copy elements from a backing dictionary to this one as accessed.

    Substitute None for deleted item.

    raise KeyError if item was None, or if item is not found in self.data or
    self.backing.
    """

    _backing: Any

    def __init__(self, loader):
        super().__init__()
        self.loader = loader
        self._backing = object  # sentinel

    @property
    def backing(self) -> Any:
        """
        Lazily load backing data.
        """
        if self._backing is object:
            self._backing = self.loader()
        return self._backing

    def __getitem__(self, key):
        try:
            value = self.data[key]
            if value is None:
                # Deletion marker. No explicit None in this dict.
                raise KeyError(key)
            return value
        except KeyError:
            self.data[key] = self.backing[key]
            return self.data[key]

    def __delitem__(self, key):
        # Store None as a deletion marker to avoid checking self.backing
        self.data[key] = None

    def into_plain(self):
        """
        Return shallow copy of changes only.
        """
        plain = self.data.copy()
        for key, value in self.data.items():
            if isinstance(value, LazyCOWDict):
                # faster to value.data.copy() (non-recursive)?
                plain[key] = value.into_plain()
        return plain

    def apply(self):
        """
        Return shallow copy of backing with changes applied.
        """
        try:
            applied = self.backing.copy()
        except KeyError:  # when backing has no repodata["signatures"] e.g.
            applied = {}
        for key, value in self.items():
            if isinstance(value, LazyCOWDict):
                applied_value = value.apply()
                # only set "signatures" or other missing parent key if changed
                if "key" in applied or applied_value:
                    applied[key] = applied_value
            elif value is not None:
                applied[key] = value
            else:
                del applied[key]
        return applied


class RepodataPatchAccumulator(LazyCOWDict):
    groups = "packages", "packages.conda", "signatures"

    # conda-content-trust adds another filename/packages object at the top level.
    # "signatures": {
    # "_anaconda_depends-2018.12-py27_0.tar.bz2": {
    # ...

    def __init__(self, loader, previous=None):
        """
        loader: Function loading or returning cached repodata.json
        previous: Accumulated patches from an earlier run.
        """
        super().__init__(loader)

        if not previous:
            previous = {}

        self.data.update(previous)

        def sub_loader(key):
            """
            Function returning value or empty placeholder from loader().
            """

            def load():
                return loader().get(key, {})

            return load

        for group in self.groups:
            self.data[group] = LazyCOWDict(sub_loader(group))
            self.data[group].update(previous.get(group, {}))


def demonstration():
    global patched_repodata

    from conda.gateways.repodata.jlap.core import JLAP
    from conda.gateways.repodata.jlap.fetch import (
        apply_patches,
        find_patches,
        hash,
    )

    repodata = REPODATA_PATH.read_bytes()
    repodata_hash = hash()
    repodata_hash.update(repodata)
    have_hash = repodata_hash.hexdigest()
    print(f"Unpatched repodata hash is {have_hash}")

    patched_repodata = RepodataPatchAccumulator(JSONLoader(REPODATA_PATH))
    assert isinstance(patched_repodata["packages"], UserDict)
    assert isinstance(patched_repodata["packages.conda"], UserDict)

    # will into_plain() or apply() mutate the loader so that it should no longer
    # be used?
    def repodata_stats(repodata, note):
        log.info(
            f"{note} has {len(repodata)} keys, {len(repodata['packages'])} packages, {len(repodata['packages.conda'])} packages.conda, signatures? {'signatures' in repodata}"
        )

    repodata_stats(patched_repodata.backing, "backing before apply()")

    with timeme("Parse JLAP and apply patches"):
        jlap = JLAP.from_path(REPODATA_JLAP_PATH)
        patches = list(json.loads(patch) for _, patch, _ in jlap.body)

        footer = json.loads(jlap.penultimate[1])
        print(footer)

        want_hash = footer["latest"]
        needed_patches = find_patches(patches, have_hash, want_hash)
        print(f"{len(needed_patches)} patches to apply out of {len(patches)} available")

        # apply_patches() pops patches off the end of its list. Reverse when
        # applying patches one-by-one for debugging.
        for patch in reversed(needed_patches):
            if SHOW_PATCH_STEPS:
                for step in patch["patch"]:
                    log.info("%s %s", step["op"], step["path"])
            try:
                # apply_patches expects a jlap-format wrapper and may not
                # operate in SHOW_PATCH_STEPS order, above; for single patches
                # (or single patches broken further down into steps which are
                # also valid jsonpatch), try data =
                # jsonpatch.JsonPatch(patch["patch"]).apply(data, in_place=True)
                apply_patches(patched_repodata, [patch])
            except (JsonPointerException, JsonPatchException) as e:
                # Exception tends to print entire "packages" or "packages.conda".
                # Just print the class, maybe the op and path?
                print(f"Patch failed with {type(e)}. Download repodata.json.zst?")
                break

    collected_patches = dumps(
        patched_repodata.into_plain(),
    )
    # need human_bytes function
    print(f"{len(repodata)} base length")
    print(f"{len(collected_patches)} overlay length")

    with timeme("Write collected changes to file "):
        REPODATA_PATH.with_suffix(".patch.json").write_text(
            dumps(patched_repodata.into_plain())
        )

    with timeme("Write the original back to a file "):
        REPODATA_PATH.with_suffix(".time_write").write_text(
            dumps(patched_repodata.loader())
        )

    repodata_stats(patched_repodata.backing, "backing before apply()")

    repodata_stats(
        patched_repodata.into_plain(),
        "plain dictionary patches-only before apply() was called",
    )

    # what we'd write for compat with single-cache-file users or hand to
    # SubdirData
    applied = patched_repodata.apply()

    repodata_stats(patched_repodata.backing, "backing after apply()")

    repodata_stats(applied, "patched repodata")

    repodata_stats(
        patched_repodata.into_plain(),
        "plain dictionary 'without'? patches, after apply() was called",
    )


if __name__ == "__main__":
    # log with millisecond timestamps
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # logging.getLogger("conda.gateways.repodata").setLevel(logging.DEBUG)
    log.setLevel(logging.DEBUG)

    large = True
    if large:
        REPODATA_PATH = Path(__file__).parent / "linux-64-repodata.json"
        REPODATA_JLAP_PATH = Path(__file__).parent / "linux-64-repodata-3.jlap"
    else:
        REPODATA_PATH = Path("noarch-repodata.json")
        REPODATA_JLAP_PATH = Path("noarch-repodata.jlap")

    demonstration()
