# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context
from conda.common.compat import on_win
from conda.common.path import (
    get_major_minor_version,
    missing_pyc_files,
    path_identity,
    unix_path_to_win,
    url_to_path,
    win_path_backout,
    win_path_to_unix,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Iterable

    from pytest_mock import MockerFixture

    from conda.testing import TmpEnvFixture

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


def test_path_translations():
    paths = [
        (
            r"z:\miniconda\Scripts\pip.exe",
            "/z/miniconda/Scripts/pip.exe",
            "/cygdrive/z/miniconda/Scripts/pip.exe",
        ),
        (
            r"z:\miniconda;z:\Documents (x86)\pip.exe;c:\test",
            "/z/miniconda:/z/Documents (x86)/pip.exe:/c/test",
            "/cygdrive/z/miniconda:/cygdrive/z/Documents (x86)/pip.exe:/cygdrive/c/test",
        ),
        # Failures:
        # (r"z:\miniconda\Scripts\pip.exe",
        #  "/z/miniconda/Scripts/pip.exe",
        #  "/cygdrive/z/miniconda/Scripts/pip.exe"),
        # ("z:\\miniconda\\",
        #  "/z/miniconda/",
        #  "/cygdrive/z/miniconda/"),
        (
            "test dummy text /usr/bin;z:\\documents (x86)\\code\\conda\\tests\\envskhkzts\\test1;z:\\documents\\code\\conda\\tests\\envskhkzts\\test1\\cmd more dummy text",
            "test dummy text /usr/bin:/z/documents (x86)/code/conda/tests/envskhkzts/test1:/z/documents/code/conda/tests/envskhkzts/test1/cmd more dummy text",
            "test dummy text /usr/bin:/cygdrive/z/documents (x86)/code/conda/tests/envskhkzts/test1:/cygdrive/z/documents/code/conda/tests/envskhkzts/test1/cmd more dummy text",
        ),
    ]
    for windows_path, unix_path, cygwin_path in paths:
        assert win_path_to_unix(windows_path) == unix_path
        assert unix_path_to_win(unix_path) == windows_path

        # assert utils.win_path_to_cygwin(windows_path, root="/cygdrive") == cygwin_path
        # assert utils.cygwin_path_to_win(cygwin_path) == windows_path


def test_text_translations():
    test_win_text = "z:\\msarahan\\code\\conda\\tests\\envsk5_b4i\\test 1"
    test_unix_text = "/z/msarahan/code/conda/tests/envsk5_b4i/test 1"
    assert test_win_text == unix_path_to_win(test_unix_text)
    assert test_unix_text == win_path_to_unix(test_win_text)


@pytest.mark.skipif(
    not on_win,
    reason="win_path_to_unix is path_identity on non-windows",
)
@pytest.mark.parametrize(
    "paths,expected",
    [
        # falsy
        pytest.param(None, [None], id="None"),
        pytest.param("", ["."], id="empty string"),
        pytest.param((), [()], id="empty tuple"),
        # native
        pytest.param(
            "C:\\path\\to\\One",
            [
                "/c/path/to/One",  # MSYS2
                "/cygdrive/c/path/to/One",  # cygwin
            ],
            id="path",
        ),
        pytest.param(
            ["C:\\path\\to\\One"],
            [
                ("/c/path/to/One",),  # MSYS2
                ("/cygdrive/c/path/to/One",),  # cygwin
            ],
            id="list[path]",
        ),
        pytest.param(
            ("C:\\path\\to\\One", "C:\\path\\Two", "\\\\mount\\Three"),
            [
                ("/c/path/to/One", "/c/path/Two", "//mount/Three"),  # MSYS2
                (
                    "/cygdrive/c/path/to/One",
                    "/cygdrive/c/path/Two",
                    "//mount/Three",
                ),  # cygwin
            ],
            id="tuple[path, ...]",
        ),
        pytest.param(
            "C:\\path\\to\\One;C:\\path\\Two;\\\\mount\\Three",
            [
                "/c/path/to/One:/c/path/Two://mount/Three",  # MSYS2
                "/cygdrive/c/path/to/One:/cygdrive/c/path/Two://mount/Three",  # cygwin
            ],
            id="path;...",
        ),
    ],
)
@pytest.mark.parametrize(
    "cygpath",
    [pytest.param(True, id="cygpath"), pytest.param(False, id="fallback")],
)
def test_win_path_to_unix(
    mocker: MockerFixture,
    paths: str | Iterable[str] | None,
    expected: list[str | list[str] | None],
    cygpath: bool,
) -> None:
    if not cygpath:
        # test without cygpath
        mocker.patch("subprocess.run", side_effect=FileNotFoundError)

    assert win_path_to_unix(paths) in expected


@pytest.mark.skipif(
    not on_win,
    reason="win_path_to_unix is path_identity on non-windows",
)
@pytest.mark.parametrize(
    "paths,expected",
    [
        # falsy
        pytest.param(None, None, id="None"),
        pytest.param("", ".", id="empty string"),
        pytest.param((), (), id="empty tuple"),
        # MSYS2
        pytest.param(
            # 1 leading slash = root
            "/",
            "{WINDOWS}\\Library\\",
            id="root",
        ),
        pytest.param(
            # 1 leading slash + 1 letter = drive
            "/c",
            "C:\\",
            id="drive",
        ),
        pytest.param(
            # 1 leading slash + 1 letter = drive
            "/c/",
            "C:\\",
            id="drive [trailing]",
        ),
        pytest.param(
            # 1 leading slash + 2+ letters = root path
            "/root",
            "{WINDOWS}\\Library\\root",
            id="root path",
        ),
        pytest.param(
            # 1 leading slash + 2+ letters = root path
            "/root/",
            "{WINDOWS}\\Library\\root\\",
            id="root path [trailing]",
        ),
        pytest.param(
            # 2 leading slashes = UNC mount
            "//",
            "\\\\",
            id="bare UNC mount",
        ),
        pytest.param(
            # 2 leading slashes = UNC mount
            "//mount",
            "\\\\mount",
            id="UNC mount",
        ),
        pytest.param(
            # 2 leading slashes = UNC mount
            "//mount/",
            "\\\\mount\\",
            id="UNC mount [trailing]",
        ),
        pytest.param(
            # 3+ leading slashes = root
            "///",
            "{WINDOWS}\\Library\\",
            id="root [leading]",
        ),
        pytest.param(
            # 3+ leading slashes = root path
            "///root",
            "{WINDOWS}\\Library\\root",
            id="root path [leading]",
        ),
        pytest.param(
            # 3+ leading slashes = root
            "////",
            "{WINDOWS}\\Library\\",
            id="root [leading, trailing]",
        ),
        pytest.param(
            # 3+ leading slashes = root path
            "///root/",
            "{WINDOWS}\\Library\\root\\",
            id="root path [leading, trailing]",
        ),
        pytest.param(
            # a normal path
            "/c/path/to/One",
            "C:\\path\\to\\One",
            id="normal path",
        ),
        pytest.param(
            # a normal path
            "/c//path///to////One",
            "C:\\path\\to\\One",
            id="normal path [extra]",
        ),
        pytest.param(
            # a normal path
            "/c/path/to/One/",
            "C:\\path\\to\\One\\",
            id="normal path [trailing]",
        ),
        pytest.param(
            # a normal UNC path
            "//mount/to/One",
            "\\\\mount\\to\\One",
            id="UNC path",
        ),
        pytest.param(
            # a normal UNC path
            "//mount//to///One",
            "\\\\mount\\to\\One",
            id="UNC path [extra]",
        ),
        pytest.param(
            # a normal root path
            "/path/to/One",
            "{WINDOWS}\\Library\\path\\to\\One",
            id="root path",
        ),
        pytest.param(
            # a normal root path
            "/path//to///One",
            "{WINDOWS}\\Library\\path\\to\\One",
            id="root path [extra]",
        ),
        pytest.param(
            # relative path stays relative
            "relative/path/to/One",
            "relative\\path\\to\\One",
            id="relative",
        ),
        pytest.param(
            # relative path stays relative
            "relative//path///to////One",
            "relative\\path\\to\\One",
            id="relative [extra]",
        ),
        pytest.param(
            "/c/path/to/One://path/to/One:/path/to/One:relative/path/to/One",
            (
                "C:\\path\\to\\One;"
                "\\\\path\\to\\One;"
                "{WINDOWS}\\Library\\path\\to\\One;"
                "relative\\path\\to\\One"
            ),
            id="path;...",
        ),
        pytest.param(
            ["/c/path/to/One"],
            ("C:\\path\\to\\One",),
            id="list[path]",
        ),
        pytest.param(
            ("/c/path/to/One", "/c/path/Two", "//mount/Three"),
            ("C:\\path\\to\\One", "C:\\path\\Two", "\\\\mount\\Three"),
            id="tuple[path, ...]",
        ),
        # XXX Cygwin and MSYS2's cygpath programs are not mutually
        # aware meaning that MSYS2's cygpath treats
        # /cygrive/c/here/there as a regular absolute path and returns
        # {prefix}\Library\cygdrive\c\here\there.  And vice versa.
        #
        # cygwin
        # pytest.param(
        #     "/cygdrive/c/path/to/One",
        #     "C:\\path\\to\\One",
        #     id="Cygwin drive letter path (cygwin)",
        # ),
        # pytest.param(
        #     ["/cygdrive/c/path/to/One"],
        #     ("C:\\path\\to\\One",),
        #     id="list[path] (cygwin)",
        # ),
        # pytest.param(
        #     ("/cygdrive/c/path/to/One", "/cygdrive/c/path/Two", "//mount/Three"),
        #     ("C:\\path\\to\\One", "C:\\path\\Two", "\\\\mount\\Three"),
        #     id="tuple[path, ...] (cygwin)",
        # ),
    ],
)
@pytest.mark.parametrize(
    "unix",
    [
        pytest.param(True, id="Unix"),
        pytest.param(False, id="Windows"),
    ],
)
@pytest.mark.parametrize(
    "cygpath",
    [pytest.param(True, id="cygpath"), pytest.param(False, id="fallback")],
)
def test_unix_path_to_win(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    paths: str | Iterable[str] | None,
    expected: str | tuple[str, ...] | None,
    unix: bool,
    cygpath: bool,
) -> None:
    windows_prefix = context.target_prefix
    unix_prefix = win_path_to_unix(windows_prefix)

    def format(path: str) -> str:
        return path.format(UNIX=unix_prefix, WINDOWS=windows_prefix)

    prefix = unix_prefix if unix else windows_prefix
    if expected:
        expected = (
            tuple(map(format, expected))
            if isinstance(expected, tuple)
            else format(expected)
        )

    if not cygpath:
        # test without cygpath
        mocker.patch("subprocess.run", side_effect=FileNotFoundError)

    assert unix_path_to_win(paths, prefix) == expected
