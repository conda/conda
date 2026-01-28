# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import ntpath
import re
from contextlib import nullcontext
from logging import getLogger
from pathlib import PureWindowsPath
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context
from conda.common import path
from conda.common.compat import on_win
from conda.common.path import (
    get_major_minor_version,
    missing_pyc_files,
    path_identity,
    strip_pkg_extension,
    unix_path_to_win,
    url_to_path,
    win_path_backout,
    win_path_to_unix,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from pytest_mock import MockerFixture

log = getLogger(__name__)


def test_url_to_path_unix():
    assert url_to_path("file:///etc/fstab") == "/etc/fstab"
    assert url_to_path("file://localhost/etc/fstab") == "/etc/fstab"
    assert url_to_path("file://127.0.0.1/etc/fstab") == "/etc/fstab"
    assert url_to_path("file://::1/etc/fstab") == "/etc/fstab"


def test_url_to_path_windows_local():
    assert url_to_path("file:///c|/WINDOWS/notepad.exe") == "c:/WINDOWS/notepad.exe"
    assert url_to_path("file:///C:/WINDOWS/notepad.exe") == "C:/WINDOWS/notepad.exe"
    assert (
        url_to_path("file://localhost/C|/WINDOWS/notepad.exe")
        == "C:/WINDOWS/notepad.exe"
    )
    assert (
        url_to_path("file://localhost/c:/WINDOWS/notepad.exe")
        == "c:/WINDOWS/notepad.exe"
    )
    assert url_to_path("C:\\Windows\\notepad.exe") == "C:\\Windows\\notepad.exe"
    assert (
        url_to_path("file:///C:/Program%20Files/Internet%20Explorer/iexplore.exe")
        == "C:/Program Files/Internet Explorer/iexplore.exe"
    )
    assert (
        url_to_path("C:\\Program Files\\Internet Explorer\\iexplore.exe")
        == "C:\\Program Files\\Internet Explorer\\iexplore.exe"
    )


def test_url_to_path_windows_unc():
    assert (
        url_to_path("file://windowshost/windowshare/path")
        == "//windowshost/windowshare/path"
    )
    assert (
        url_to_path("\\\\windowshost\\windowshare\\path")
        == "\\\\windowshost\\windowshare\\path"
    )
    assert (
        url_to_path("file://windowshost\\windowshare\\path")
        == "//windowshost\\windowshare\\path"
    )
    assert (
        url_to_path("file://\\\\machine\\shared_folder\\path\\conda")
        == "\\\\machine\\shared_folder\\path\\conda"
    )


def test_win_path_backout():
    assert (
        win_path_backout("file://\\\\machine\\shared_folder\\path\\conda")
        == "file://machine/shared_folder/path/conda"
    )
    assert (
        win_path_backout("file://\\\\machine\\shared\\ folder\\path\\conda")
        == "file://machine/shared\\ folder/path/conda"
    )


FILES = (
    "bin/flask",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/PKG-INFO",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/SOURCES.txt",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/dependency_links.txt",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/entry_points.txt",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/not-zip-safe",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/requires.txt",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/top_level.txt",
    "lib/python2.7/site-packages/flask/__init__.py",
    "lib/python2.7/site-packages/flask/__main__.py",
    "lib/python2.7/site-packages/flask/_compat.py",
    "lib/python2.7/site-packages/flask/app.py",
    "lib/python2.7/site-packages/flask/blueprints.py",
    "lib/python2.7/site-packages/flask/cli.py",
    "lib/python2.7/site-packages/flask/config.py",
    "lib/python2.7/site-packages/flask/ctx.py",
    "lib/python2.7/site-packages/flask/debughelpers.py",
    "lib/python2.7/site-packages/flask/ext/__init__.py",
)


def test_missing_pyc_files_27():
    missing = missing_pyc_files("27", FILES)
    assert len(missing) == 10
    assert tuple(m[1] for m in missing) == (
        "lib/python2.7/site-packages/flask/__init__.pyc",
        "lib/python2.7/site-packages/flask/__main__.pyc",
        "lib/python2.7/site-packages/flask/_compat.pyc",
        "lib/python2.7/site-packages/flask/app.pyc",
        "lib/python2.7/site-packages/flask/blueprints.pyc",
        "lib/python2.7/site-packages/flask/cli.pyc",
        "lib/python2.7/site-packages/flask/config.pyc",
        "lib/python2.7/site-packages/flask/ctx.pyc",
        "lib/python2.7/site-packages/flask/debughelpers.pyc",
        "lib/python2.7/site-packages/flask/ext/__init__.pyc",
    )


def test_missing_pyc_files_34():
    missing = missing_pyc_files("34", FILES)
    assert len(missing) == 10
    assert tuple(m[1] for m in missing) == (
        "lib/python2.7/site-packages/flask/__pycache__/__init__.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/__main__.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/_compat.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/app.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/blueprints.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/cli.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/config.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/ctx.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/debughelpers.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/ext/__pycache__/__init__.cpython-34.pyc",
    )


def test_missing_pyc_files_35():
    missing = missing_pyc_files("35", FILES)
    assert len(missing) == 10
    assert tuple(m[1] for m in missing) == (
        "lib/python2.7/site-packages/flask/__pycache__/__init__.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/__main__.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/_compat.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/app.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/blueprints.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/cli.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/config.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/ctx.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/debughelpers.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/ext/__pycache__/__init__.cpython-35.pyc",
    )


def test_get_major_minor_version_no_dot():
    assert get_major_minor_version("3.5.2") == "3.5"
    assert get_major_minor_version("27") == "2.7"
    assert get_major_minor_version("bin/python2.7") == "2.7"
    assert get_major_minor_version("lib/python34/site-packages/") == "3.4"
    assert get_major_minor_version("python3") is None

    assert get_major_minor_version("3.10.0") == "3.10"
    assert get_major_minor_version("310") == "3.10"
    assert get_major_minor_version("bin/python3.10") == "3.10"
    assert get_major_minor_version("lib/python310/site-packages/") == "3.10"
    assert get_major_minor_version("python3") is None

    assert get_major_minor_version("3.5.2", False) == "35"
    assert get_major_minor_version("27", False) == "27"
    assert get_major_minor_version("bin/python2.7", False) == "27"
    assert get_major_minor_version("lib/python34/site-packages/", False) == "34"
    assert get_major_minor_version("python3", False) is None

    assert get_major_minor_version("3.10.0", False) == "310"
    assert get_major_minor_version("310", False) == "310"
    assert get_major_minor_version("bin/python3.10", False) == "310"
    assert get_major_minor_version("lib/python310/site-packages/", False) == "310"
    assert get_major_minor_version("python3", False) is None


def test_path_identity(tmp_path: Path) -> None:
    # None
    assert path_identity(None) is None

    # str | os.PathLike
    assert path_identity("") == "."
    assert path_identity(".") == "."
    assert path_identity("./") == "."
    assert path_identity("relative") == "relative"
    assert path_identity(str(tmp_path)) == str(tmp_path)
    assert path_identity(tmp_path) == str(tmp_path)

    # Iterable[str | os.PathLike]
    assert path_identity(("", ".", "./", "relative", str(tmp_path), tmp_path)) == (
        ".",
        ".",
        ".",
        "relative",
        str(tmp_path),
        str(tmp_path),
    )


@pytest.mark.parametrize(
    "paths,expected",
    [
        pytest.param(None, None, id="None"),
        pytest.param((), (), id="empty tuple"),
        pytest.param([], (), id="empty list"),
        pytest.param({}, (), id="empty dict"),
        pytest.param(set(), (), id="empty set"),
    ],
)
def test_path_conversion_falsy(
    paths: str | Iterable[str] | None, expected: str | Iterable[str] | None
) -> None:
    assert win_path_to_unix(paths) == expected
    assert unix_path_to_win(paths) == expected


@pytest.mark.parametrize(
    # NOTE: we automatically test for paths with redundant slashes
    # NOTE: for windows paths we offer two roots for testing:
    #         - ROOT (resolved path), e.g., Z:\\root
    #         - ALT (unresolved path), e.g., Z:\\non_root\\.\\..\\root
    "unix,win,roundtrip",
    # there are three patterns in the parameterized tests:
    #   unix → win → unix (roundtrip), defined as (<unix>, <win>, True)
    #   only unix → win (no roundtrip), defined as (<unix>, <win>, None)
    #   only win → unix (no roundtrip), defined as (None, <win>, <unix>)
    [
        # cwd
        pytest.param(".", ".", True, id="cwd"),
        pytest.param("", ".", None, id="cwd"),
        pytest.param(None, "", ".", id="cwd"),
        pytest.param("./", ".\\", True, id="cwd"),
        # root (1 or 3+ leading slashes)
        pytest.param("/", "{ROOT}\\", True, id="root"),
        pytest.param("///", "{ROOT}\\", None, id="root"),
        pytest.param("////", "{ROOT}\\", None, id="root"),
        pytest.param(None, "{ALT}\\", "/", id="root"),
        pytest.param("/root", "{ROOT}\\root", True, id="root"),
        pytest.param("///root", "{ROOT}\\root", None, id="root"),
        pytest.param("////root", "{ROOT}\\root", None, id="root"),
        pytest.param(None, "{ALT}\\root", "/root", id="root"),
        pytest.param("/root/", "{ROOT}\\root\\", True, id="root"),
        pytest.param("///root/", "{ROOT}\\root\\", None, id="root"),
        pytest.param("////root/", "{ROOT}\\root\\", None, id="root"),
        pytest.param(None, "{ALT}\\root\\", "/root/", id="root"),
        pytest.param("/root/CaSe", "{ROOT}\\root\\CaSe", True, id="root"),
        pytest.param("///root/CaSe", "{ROOT}\\root\\CaSe", None, id="root"),
        pytest.param(None, "{ALT}\\root\\CaSe", "/root/CaSe", id="root"),
        # UNC mount (2 leading slashes)
        pytest.param("//", "\\\\", True, id="UNC"),
        pytest.param("//mount", "\\\\mount", True, id="UNC"),
        pytest.param("//mount/", "\\\\mount\\", True, id="UNC"),
        pytest.param("//mount//", "\\\\mount\\", None, id="UNC"),
        pytest.param(None, "\\\\mount\\", "//mount/", id="UNC"),
        pytest.param("//mount/CaSe", "\\\\mount\\CaSe", True, id="UNC"),
        pytest.param("//mount//CaSe", "\\\\mount\\CaSe", None, id="UNC"),
        pytest.param(None, "\\\\mount\\CaSe", "//mount/CaSe", id="UNC"),
        # drive (1 leading slash + 1 letter)
        # /c & /C doesn't roundtrip because the normal form is /c/ -- see below
        pytest.param("/c", "C:\\", None, id="drive"),
        pytest.param("/C", "C:\\", None, id="drive"),
        # c: & C: doesn't roundtrip because the normal form is c:\ -- see below
        pytest.param(None, "c:", "/c", id="drive"),
        pytest.param(None, "C:", "/c", id="drive"),
        pytest.param("/c/", "C:\\", True, id="drive"),
        pytest.param("/C/", "C:\\", None, id="drive"),
        pytest.param("/c//", "C:\\", None, id="drive"),
        pytest.param("/C//", "C:\\", None, id="drive"),
        pytest.param(None, "c:\\", "/c/", id="drive"),
        pytest.param(None, "C:\\", "/c/", id="drive"),
        pytest.param("/c/drive", "C:\\drive", True, id="drive"),
        pytest.param(None, "c:\\drive", "/c/drive", id="drive"),
        pytest.param(None, "C:\\drive", "/c/drive", id="drive"),
        pytest.param(None, "c:\\drive", "/c/drive", id="drive"),
        pytest.param("/c/drive/CaSe", "C:\\drive\\CaSe", True, id="drive"),
        pytest.param(None, "c:\\drive\\CaSe", "/c/drive/CaSe", id="drive"),
        # relative path
        pytest.param("relative", "relative", True, id="relative"),
        pytest.param("relative/", "relative\\", True, id="relative"),
        pytest.param("relative/CaSe", "relative\\CaSe", True, id="relative"),
        # PATH forms
        pytest.param("path:", "path;.", None, id="PATH"),
        pytest.param(None, "path;.", "path:.", id="PATH"),
        pytest.param(None, "path;", "path", id="PATH"),
        pytest.param("path::", "path;.;.", None, id="PATH"),
        pytest.param("path:.:.", "path;.;.", True, id="PATH"),
        pytest.param(None, "path;;", "path", id="PATH"),
        pytest.param("path::other", "path;.;other", None, id="PATH"),
        pytest.param(None, "path;;other", "path:other", id="PATH"),
        pytest.param("path:.:other", "path;.;other", True, id="PATH"),
        pytest.param(":path", ".;path", None, id="PATH"),
        pytest.param(None, ";path", "path", id="PATH"),
        pytest.param(".:path", ".;path", True, id="PATH"),
        # cygpath errors (works with fallback)
        # pytest.param("path/../other", "path\\..\\other", True, id="parent"),
    ],
)
@pytest.mark.parametrize(
    "cygpath",
    [
        pytest.param(
            True,
            id="cygpath",
            marks=pytest.mark.skipif(
                not on_win,
                reason="cygpath is only available on Windows",
            ),
        ),
        pytest.param(False, id="fallback"),
    ],
)
def test_path_conversion(
    tmp_path: Path,
    mocker: MockerFixture,
    unix: str | None,
    win: str,
    roundtrip: str | bool | None,
    cygpath: bool,
) -> None:
    # ensure we are testing either a roundtrip, win → unix, or unix → win
    assert isinstance(win, str)
    if roundtrip in (True, None):
        # roundtrip or unix → win
        assert isinstance(unix, str)
    else:
        # win → unix
        assert unix is None and isinstance(roundtrip, str)

    if on_win:
        win_prefix = PureWindowsPath(context.target_prefix)
    else:
        # cygpath doesn't exist so we don't have to align with what cygpath would return
        # besides, using Unix paths and expecting a valid Windows path doesn't make sense
        win_prefix = PureWindowsPath("Z:\\fake\\prefix")

    if not cygpath:
        # test without cygpath
        mocker.patch("subprocess.run", side_effect=FileNotFoundError)

    win = win.format(
        # using `ntpath.join` instead of `pathlib` otherwise the CWD part (`.`) is consumed as a no-op
        ROOT=ntpath.join(win_prefix, "Library"),
        ALT=ntpath.join(win_prefix, ".", "..", win_prefix.name, "Library"),
    )

    def replace(path: str, sep: str) -> str:
        if match := re.match(r"^([/\\]+)(.*)$", path):
            leading, path = match.groups()
            return leading + re.sub(r"[/\\]+", re.escape(sep), path)
        return path

    if unix is not None:
        # test unix → win
        path = unix_path_to_win(unix, prefix=win_prefix)
        assert path == win, f"{unix} (to win)→ {path} ≠ {win}"

        # test unix with redundant // → win
        double = replace(unix, "/" * 2)
        path = unix_path_to_win(double, prefix=win_prefix)
        assert path == win, f"{unix} → {double} → {path} ≠ {win}"

        # test cygdrive
        # NOTE: only Cygwin cygpath can handle /cygdrive/... paths, since we expect to
        # be using MSYS2 cygpath skip testing unless testing fallback
        if unix.startswith(("/c", "/C")) and not cygpath:
            cygdrive = f"/cygdrive{unix}"
            path = unix_path_to_win(cygdrive, prefix=win_prefix, cygdrive=True)
            assert path == win, f"{unix} → {cygdrive} → {path} ≠ {win}"

    if roundtrip is not None:
        # test win → unix
        path = win_path_to_unix(win, prefix=win_prefix)
        assert isinstance(roundtrip := unix or roundtrip, str)
        assert path == roundtrip, f"{win} (to unix)→ {path} ≠ {roundtrip}"

        # test win with redundant \ → unix
        double = replace(win, "\\" * 2)
        path = win_path_to_unix(double, prefix=win_prefix)
        assert path == roundtrip, f"{win} → {double} → {path} ≠ {roundtrip}"

        # test win with forward / → unix
        forward = replace(win, "/")
        path = win_path_to_unix(forward, prefix=win_prefix)
        assert path == roundtrip, f"{win} → {forward} → {path} ≠ {roundtrip}"

        # test cygdrive
        # test cygdrive
        # NOTE: only Cygwin cygpath can handle /cygdrive/... paths, since we expect to
        # be using MSYS2 cygpath skip testing unless testing fallback
        if roundtrip.startswith(("/c", "/C")) and not cygpath:
            cygdrive = f"/cygdrive{roundtrip}"
            path = win_path_to_unix(win, prefix=win_prefix, cygdrive=True)
            assert path == cygdrive, f"{win} → {path} ≠ {cygdrive}"


@pytest.mark.parametrize(
    "function,raises",
    [
        ("is_package_file", TypeError),
        ("KNOWN_EXTENSIONS", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(path, function)()


@pytest.mark.parametrize(
    "path,expected_base,expected_ext",
    [
        # .tar.bz2 packages
        (
            "/path/numpy-1.26.4-py312h8753938_0.tar.bz2",
            "/path/numpy-1.26.4-py312h8753938_0",
            ".tar.bz2",
        ),
        (
            "requests-2.32.3-py313h06a4308_0.tar.bz2",
            "requests-2.32.3-py313h06a4308_0",
            ".tar.bz2",
        ),
        # .conda packages
        (
            "/path/pandas-2.2.3-py312h526ad5a_1.conda",
            "/path/pandas-2.2.3-py312h526ad5a_1",
            ".conda",
        ),
        ("zlib-1.3.1-h5f15de7_0.conda", "zlib-1.3.1-h5f15de7_0", ".conda"),
        # No extension - historic behavior: returns (path, None) for graceful handling
        # of paths without known extensions. See docstring examples in strip_pkg_extension.
        (
            "/path/numpy-1.26.4-py312h8753938_0",
            "/path/numpy-1.26.4-py312h8753938_0",
            None,
        ),
        ("zlib-1.3.1-h5f15de7_0", "zlib-1.3.1-h5f15de7_0", None),
    ],
)
def test_strip_pkg_extension(
    path: str, expected_base: str, expected_ext: str | None
) -> None:
    base, ext = strip_pkg_extension(path)
    assert base == expected_base
    assert ext == expected_ext
