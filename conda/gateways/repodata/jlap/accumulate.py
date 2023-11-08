#!/usr/bin/env python
"""
Accumulate jlap patches in a single separate file, to avoid overhead of
rewriting large file each time.
"""

import json
from pathlib import Path
from conda.gateways.repodata.jlap.core import JLAP
from conda.gateways.repodata.jlap.fetch import apply_patches, find_patches, hash, timeme
from collections import UserDict
from jsonpatch import JsonPatchException
from jsonpointer import JsonPointerException
import logging


class ObserverDict(UserDict):
    """
    Copy elements from a backing dictionary to this one as accessed.

    Substitute None for deleted item.

    raise KeyError if item was None, or if item is not found in self.data or
    self.backing.
    """

    def __init__(self, backing):
        super().__init__()
        self.backing = backing

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

    def apply(self):
        """
        Return shallow copy of backing with changes applied.
        """
        applied = self.backing.copy()
        for key, value in self.items():
            if isinstance(value, ObserverDict):
                applied[key] = value.apply()
            elif value is not None:
                applied[key] = value
            else:
                del self.backing[key]
        return applied


class RepodataPatchAccumulator(ObserverDict):
    groups = "packages", "packages.conda"

    def __init__(self, repodata, previous=None):
        """
        repodata: Backing data.
        previous: Accumulated patches from an earlier run.
        """
        super().__init__(repodata)

        if not previous:
            previous = {}

        self.data.update(previous)

        for group in self.groups:
            try:
                self.data[group] = ObserverDict(repodata[group])
                self.data[group].update(previous.get(group, {}))
            except KeyError:
                self.data[group] = ObserverDict({})
                self.data[group].update(previous.get(group, {}))

    def into_plain(self):
        """
        Return dict shallow copy without backing.
        """
        plain_dict = self.data.copy()
        for group in self.groups:
            try:
                plain_dict[group] = self.data[group].data.copy()
            except KeyError:
                # not uncommon for a patch series to modify only "packages.conda"
                pass
        return plain_dict


def demonstration():
    repodata = REPODATA_PATH.read_bytes()
    with timeme("Parse repodata.json"):
        repodata_parsed = json.loads(repodata)
    repodata_hash = hash()
    repodata_hash.update(repodata)
    have_hash = repodata_hash.hexdigest()
    print(f"Unpatched repodata hash is {have_hash}")

    patched_repodata = RepodataPatchAccumulator(repodata_parsed)
    assert isinstance(patched_repodata["packages"], ObserverDict)
    assert isinstance(patched_repodata["packages.conda"], ObserverDict)

    for key in patched_repodata:
        print(key, type(patched_repodata[key]))
    print(patched_repodata)

    with timeme("Parse JLAP and apply patches"):
        jlap = JLAP.from_path(REPODATA_JLAP_PATH)
        patches = list(json.loads(patch) for _, patch, _ in jlap.body)

        if False:
            # overview of used jsonpatch features
            for patch in patches:
                for step in patch["patch"]:
                    print(step["op"], step["path"])
                    # now properly split jsonpointer into bits (the first two)

        footer = json.loads(jlap.penultimate[1])
        print(footer)

        want_hash = footer["latest"]
        needed_patches = find_patches(patches, have_hash, want_hash)
        print(f"{len(needed_patches)} patches to apply out of {len(patches)} available")

        # apply_patches() pops patches off the end of its list. Reverse when
        # applying patches one-by-one for debugging.
        for patch in reversed(needed_patches):
            for step in patch["patch"]:
                print(step["op"], step["path"])
                pass
            try:
                apply_patches(patched_repodata, [patch])
            except (JsonPointerException, JsonPatchException) as e:
                # Exception tends to print entire "packages" or "packages.conda".
                # Just print the class, maybe the op and path?
                print(f"Patch failed with {type(e)}. Download repodata.json.zst?")
                break
            # pprint.pprint(patched_repodata.data)
            print()

    collected_patches = json.dumps(
        patched_repodata.into_plain(), separators=(":", ","), sort_keys=True
    )
    # need human_bytes function
    print(f"{len(repodata)} base length")
    print(f"{len(collected_patches)} overlay length")

    with timeme("Write collected changes to file"):
        REPODATA_PATH.with_suffix(".patch.json").write_text(
            json.dumps(patched_repodata.into_plain(), indent=2, sort_keys=True)
        )

    with timeme("If we wrote the original back to a file"):
        REPODATA_PATH.with_suffix(".time_write").write_text(
            json.dumps(repodata_parsed, check_circular=True, separators=(":", ","))
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("conda.gateways.repodata").setLevel(logging.DEBUG)

    large = True
    if large:
        REPODATA_PATH = Path("linux-64-repodata.json")
        REPODATA_JLAP_PATH = Path("linux-64-repodata-2.jlap")
    else:
        REPODATA_PATH = Path("noarch-repodata.json")
        REPODATA_JLAP_PATH = Path("noarch-repodata.jlap")

    demonstration()
