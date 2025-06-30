# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.base.context import context
from conda.common.compat import on_win
from conda.common.path.windows import unix_path_to_win, win_path_to_unix

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pytest_mock import MockerFixture

    from conda.testing.fixtures import TmpEnvFixture


@pytest.mark.skipif(
    not on_win,
    reason="native_path_to_unix is path_identity on non-windows",
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
    expected: list[str | tuple[str, ...] | None],
    cygpath: bool,
) -> None:
    if not cygpath:
        # test without cygpath
        mocker.patch("subprocess.run", side_effect=FileNotFoundError)

    assert win_path_to_unix(paths) in expected


@pytest.mark.skipif(
    not on_win,
    reason="native_path_to_unix is path_identity on non-windows",
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
    "cygpath",
    [pytest.param(True, id="cygpath"), pytest.param(False, id="fallback")],
)
def test_unix_path_to_win(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    paths: str | Iterable[str] | None,
    expected: str | tuple[str, ...] | None,
    cygpath: bool,
) -> None:
    windows_prefix = context.target_prefix

    def format(path: str) -> str:
        return path.format(WINDOWS=windows_prefix)

    if expected:
        expected = (
            tuple(map(format, expected))
            if isinstance(expected, tuple)
            else format(expected)
        )

    if not cygpath:
        # test without cygpath
        mocker.patch("subprocess.run", side_effect=FileNotFoundError)

    assert unix_path_to_win(paths, windows_prefix) == expected
