# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from subprocess import run
from typing import TYPE_CHECKING

import pytest

from conda.common._os.windows import is_admin_on_windows
from conda.common.compat import on_win

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_is_admin_on_windows():
    result = is_admin_on_windows()
    if on_win:
        assert result is False or result is True
    else:
        assert result is False


def _security(path: Path) -> bytes:
    from conda.common._os.windows import get_file_security

    with path.open() as stream:
        return get_file_security(stream.fileno())


@pytest.mark.skipif(not on_win, reason="Windows file security")
def test_file_security_normalizes_descriptor_layout(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    from ctypes import (
        POINTER,
        WinDLL,
        addressof,
        byref,
        c_void_p,
        cast,
        create_string_buffer,
        get_last_error,
    )
    from ctypes.wintypes import BOOL, DWORD

    from conda.common._os import windows

    source = tmp_path / "source"
    source.touch()
    expected = _security(source)
    relative = create_string_buffer(expected)
    advapi32 = WinDLL("advapi32", use_last_error=True)
    make_absolute = advapi32.MakeAbsoluteSD
    make_absolute.argtypes = (c_void_p,) * 11
    make_absolute.restype = BOOL
    sizes = [DWORD() for _ in range(5)]
    assert not make_absolute(
        relative, *(value for size in sizes for value in (None, byref(size)))
    )
    assert get_last_error() == 122  # ERROR_INSUFFICIENT_BUFFER
    buffers = [create_string_buffer(size.value) for size in sizes]
    assert make_absolute(
        relative,
        *(
            value
            for buffer, size in zip(buffers, sizes)
            for value in (buffer, byref(size))
        ),
    )
    absolute, dacl, *_ = buffers
    set_dacl = advapi32.SetSecurityDescriptorDacl
    set_dacl.argtypes = (c_void_p, BOOL, c_void_p, BOOL)
    set_dacl.restype = BOOL
    assert set_dacl(absolute, True, dacl, True)

    def get_security(*args):
        cast(args[-1], POINTER(c_void_p))[0] = addressof(absolute)
        return 0

    release = windows.LocalFree
    mocker.patch.object(windows, "GetSecurityInfo", side_effect=get_security)
    mocker.patch.object(
        windows,
        "LocalFree",
        side_effect=lambda value: (
            None if value.value == addressof(absolute) else release(value)
        ),
    )

    assert absolute.raw != relative.raw
    assert _security(source) == expected


@pytest.mark.skipif(not on_win, reason="Windows file security")
@pytest.mark.parametrize(
    "conversion",
    (
        "ConvertSecurityDescriptorToStringSecurityDescriptor",
        "ConvertStringSecurityDescriptorToSecurityDescriptor",
    ),
)
def test_security_descriptor_conversion_failure_releases_buffers(
    tmp_path: Path, mocker: MockerFixture, conversion: str
) -> None:
    from conda.common._os import windows

    source = tmp_path / "source"
    source.touch()
    release = mocker.spy(windows, "LocalFree")
    mocker.patch.object(windows, conversion, return_value=False)
    with pytest.raises(OSError):
        _security(source)

    assert release.call_count == 3
    source.unlink()


@pytest.mark.skipif(not on_win, reason="Windows file security")
@pytest.mark.parametrize(
    ("inheritance", "inherited_denial"),
    [(None, False), ("e", False), ("d", False), ("e", True)],
)
def test_create_file_preserves_security(
    tmp_path: Path, inheritance: str | None, inherited_denial: bool
) -> None:
    from conda.common._os.windows import (
        create_file_with_security,
        get_file_security,
    )

    if inherited_denial:
        run(
            ["icacls", str(tmp_path), "/deny", "*S-1-5-7:(OI)(CI)(R)"],
            check=True,
            capture_output=True,
            text=True,
        )
    source = tmp_path / "source"
    source.write_text("original")
    if inheritance is not None:
        run(
            ["icacls", str(source), f"/inheritance:{inheritance}"],
            check=True,
            capture_output=True,
            text=True,
        )
    if inheritance is not None and not inherited_denial:
        run(
            ["icacls", str(source), "/deny", "*S-1-5-7:(R)"],
            check=True,
            capture_output=True,
            text=True,
        )
    before = _security(source)
    candidate = tmp_path / "candidate"
    fd = create_file_with_security(candidate, before)
    with os.fdopen(fd, "w") as stream:
        assert os.fstat(stream.fileno()).st_size == 0
        assert get_file_security(stream.fileno()) == before
        with pytest.raises(PermissionError):
            candidate.read_text()
        stream.write("updated")
    os.replace(candidate, source)

    assert _security(source) == before
    assert source.read_text() == "updated"


@pytest.mark.skipif(not on_win, reason="Windows integrity labels")
def test_create_file_preserves_integrity_label(tmp_path: Path) -> None:
    from ctypes import byref, c_wchar_p, create_string_buffer

    from conda.common._os import windows

    source = tmp_path / "source"
    source.touch()
    before = _security(source)
    run(
        ["icacls", str(source), "/setintegritylevel", "L"],
        check=True,
        capture_output=True,
        text=True,
    )
    labeled = _security(source)
    assert labeled != before
    label = c_wchar_p()
    try:
        assert windows.ConvertSecurityDescriptorToStringSecurityDescriptor(
            create_string_buffer(labeled), 1, 0x10, byref(label), None
        )
        assert "(ML;;NW;;;LW)" in label.value
    finally:
        windows.LocalFree(label)
    candidate = tmp_path / "candidate"
    os.close(windows.create_file_with_security(candidate, labeled))

    assert _security(candidate) == labeled


@pytest.mark.skipif(not on_win, reason="Windows file security")
@pytest.mark.parametrize("failure", ("set", "query", "mismatch", "descriptor"))
def test_create_file_security_failure_cleans_candidate(
    tmp_path: Path, mocker: MockerFixture, failure: str
) -> None:
    from conda.common._os.windows import create_file_with_security

    source = tmp_path / "source"
    source.write_text("original")
    before = _security(source)
    candidate = tmp_path / "candidate"
    if failure == "set":
        run(
            ["icacls", str(source), "/inheritance:e"],
            check=True,
            capture_output=True,
            text=True,
        )
        before = _security(source)
        mocker.patch("conda.common._os.windows.SetSecurityInfo", return_value=5)
    elif failure == "query":
        mocker.patch(
            "conda.common._os.windows.get_file_security",
            side_effect=OSError("security query failed"),
        )
    elif failure == "mismatch":
        mocker.patch("conda.common._os.windows.get_file_security", return_value=b"")
    else:
        mocker.patch("msvcrt.open_osfhandle", side_effect=OSError("descriptor failed"))

    with pytest.raises(OSError):
        create_file_with_security(candidate, before)

    assert not candidate.exists()
    assert source.read_text() == "original"
    candidate.write_text("available")


@pytest.mark.skipif(not on_win, reason="Windows file security")
def test_create_file_preserves_existing_candidate(tmp_path: Path) -> None:
    from conda.common._os.windows import create_file_with_security

    source = tmp_path / "source"
    source.touch()
    candidate = tmp_path / "candidate"
    candidate.write_text("existing")

    with pytest.raises(FileExistsError):
        create_file_with_security(candidate, _security(source))

    assert candidate.read_text() == "existing"


@pytest.mark.skipif(not on_win, reason="Windows file security")
def test_create_file_cleanup_failure_keeps_candidate_empty(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    from conda.common._os.windows import create_file_with_security

    source = tmp_path / "source"
    source.write_text("original")
    before = _security(source)
    candidate = tmp_path / "candidate"
    mocker.patch("conda.common._os.windows.get_file_security", return_value=b"")
    mocker.patch("pathlib.Path.unlink", side_effect=PermissionError("cleanup denied"))

    with pytest.raises(PermissionError, match="cleanup denied") as error:
        create_file_with_security(candidate, before)

    assert "preserve file security" in str(error.value.__context__)
    assert source.read_text() == "original"
    assert candidate.read_text() == ""


@pytest.mark.skipif(not on_win, reason="Windows EFS")
def test_create_file_preserves_efs(tmp_path: Path) -> None:
    from ctypes import (
        POINTER,
        WinError,
        byref,
        c_wchar_p,
        create_unicode_buffer,
        windll,
    )
    from ctypes.wintypes import BOOL, DWORD
    from stat import FILE_ATTRIBUTE_ENCRYPTED

    from conda.common._os.windows import create_file_with_security

    get_volume_path = windll.kernel32.GetVolumePathNameW
    get_volume_path.argtypes = (c_wchar_p, c_wchar_p, DWORD)
    get_volume_path.restype = BOOL
    volume = create_unicode_buffer(32768)
    if not get_volume_path(str(tmp_path), volume, len(volume)):
        raise WinError()
    get_volume_information = windll.kernel32.GetVolumeInformationW
    get_volume_information.argtypes = (
        c_wchar_p,
        c_wchar_p,
        DWORD,
        POINTER(DWORD),
        POINTER(DWORD),
        POINTER(DWORD),
        c_wchar_p,
        DWORD,
    )
    get_volume_information.restype = BOOL
    flags = DWORD()
    if not get_volume_information(volume, None, 0, None, None, byref(flags), None, 0):
        raise WinError()
    if not flags.value & 0x20000:  # FILE_SUPPORTS_ENCRYPTION
        pytest.skip("The test volume does not support EFS")

    source = tmp_path / "source"
    source.write_text("original")
    encrypt = windll.advapi32.EncryptFileW
    encrypt.argtypes = (c_wchar_p,)
    encrypt.restype = BOOL
    if not encrypt(str(source)):
        raise WinError()
    before = _security(source)
    candidate = tmp_path / "candidate"
    fd = create_file_with_security(candidate, before, encrypted_source=source)
    with os.fdopen(fd, "w") as stream:
        assert os.fstat(stream.fileno()).st_size == 0
        assert os.fstat(stream.fileno()).st_file_attributes & FILE_ATTRIBUTE_ENCRYPTED
        stream.write("updated")
    os.replace(candidate, source)

    assert source.stat().st_file_attributes & FILE_ATTRIBUTE_ENCRYPTED
    assert _security(source) == before
    assert source.read_text() == "updated"


@pytest.mark.skipif(not on_win, reason="Windows EFS")
def test_create_file_efs_failure_preserves_source(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    from conda.common._os.windows import create_file_with_security

    source = tmp_path / "source"
    source.write_text("original")
    before = _security(source)
    candidate = tmp_path / "candidate"
    mocker.patch("conda.common._os.windows.DuplicateEncryptionInfoFile", return_value=5)

    with pytest.raises(PermissionError):
        create_file_with_security(candidate, before, encrypted_source=source)

    assert source.read_text() == "original"
    assert _security(source) == before
    assert not candidate.exists()
