# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import errno
from contextlib import nullcontext
from shutil import copyfile

import pytest

from conda.gateways.disk import create


@pytest.mark.parametrize(
    "function,raises",
    [
        ("create_application_entry_point", TypeError),
        ("ProgressFileWrapper", TypeError),
        ("create_fake_executable_softlink", TypeError),
        ("extract_tarball", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(create, function)()


def test_copy_uses_clonefile_on_macos(monkeypatch: pytest.MonkeyPatch, tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_text("contents")
    clone_calls = []

    class CloneFile:
        argtypes = None
        restype = None

        def __call__(self, src, dst, flags):
            clone_calls.append((src, dst, flags))
            copyfile(src, dst)
            return 0

    class LibC:
        clonefile = CloneFile()

    monkeypatch.setattr(create, "on_mac", True)
    monkeypatch.setattr(create, "CDLL", lambda *args, **kwargs: LibC())
    monkeypatch.setattr(
        create,
        "_do_copy",
        lambda src, dst: pytest.fail("copy fallback should not be used"),
    )
    create._CLONEFILE_UNSUPPORTED_DEVICES.clear()
    monkeypatch.setattr(create, "_CLONEFILE", None)

    create.copy(str(source), str(target))

    assert target.read_text() == "contents"
    assert clone_calls == [(bytes(source), bytes(target), 0)]


def test_copy_caches_unsupported_clonefile_device_pair(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    source = tmp_path / "source"
    target_one = tmp_path / "target-one"
    target_two = tmp_path / "target-two"
    source.write_text("contents")
    clone_calls = []
    copy_calls = []

    class CloneFile:
        argtypes = None
        restype = None

        def __call__(self, src, dst, flags):
            clone_calls.append((src, dst, flags))
            return -1

    class LibC:
        clonefile = CloneFile()

    def copy_fallback(src, dst):
        copy_calls.append((src, dst))
        copyfile(src, dst)

    monkeypatch.setattr(create, "on_mac", True)
    monkeypatch.setattr(create, "CDLL", lambda *args, **kwargs: LibC())
    monkeypatch.setattr(create, "get_errno", lambda: errno.ENOTSUP)
    monkeypatch.setattr(create, "_do_copy", copy_fallback)
    create._CLONEFILE_UNSUPPORTED_DEVICES.clear()
    monkeypatch.setattr(create, "_CLONEFILE", None)

    create.copy(str(source), str(target_one))
    create.copy(str(source), str(target_two))

    assert target_one.read_text() == "contents"
    assert target_two.read_text() == "contents"
    assert len(clone_calls) == 1
    assert copy_calls == [
        (str(source), str(target_one)),
        (str(source), str(target_two)),
    ]


def test_copy_over_existing_target_skips_clonefile(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_text("new")
    target.write_text("old")

    monkeypatch.setattr(create, "on_mac", True)
    monkeypatch.setattr(
        create,
        "CDLL",
        lambda *args, **kwargs: pytest.fail("clonefile should not be loaded"),
    )

    create.copy(str(source), str(target))

    assert target.read_text() == "new"


def test_copy_link_type_does_not_fall_back_to_hardlink(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_text("contents")
    link_calls = []

    def copy_fallback(src, dst):
        copyfile(src, dst)
        return create.LinkType.copy

    monkeypatch.setattr(create, "_clone_file", lambda *args: False)
    monkeypatch.setattr(create, "link", lambda *args: link_calls.append(args))
    monkeypatch.setattr(create, "_do_copy", copy_fallback)

    create.create_link(str(source), str(target), create.LinkType.copy)

    assert target.read_text() == "contents"
    assert target.stat().st_nlink == 1
    assert link_calls == []
