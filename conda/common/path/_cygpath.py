# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import ntpath
import posixpath
import re
from functools import partial

from ...deprecations import deprecated


def nt_to_posix(path: str, root: str, cygdrive: bool = False) -> str:
    if ntpath.pathsep in path:
        return posixpath.pathsep.join(
            nt_to_posix(path, root, cygdrive) for path in path.split(ntpath.pathsep)
        )

    # Revert in reverse order of the transformations in posix_to_nt:
    # 1. root filesystem forms:
    #      {root}\Library\root
    #    → /here/there
    # 2. mount forms:
    #      \\mount
    #    → //mount
    # 3. drive letter forms:
    #      X:\drive
    #      x:\drive
    #    → /x/drive
    #    → /cygdrive/x/drive
    # 4. anything else

    # continue performing substitutions until a match is found
    subs = 0
    if ntpath.isabs(path):
        normalized, subs = _get_RE_WIN_ROOT(root).subn(
            _to_unix_root, _nt_normpath(path)
        )
        # only keep the normalized path if the root was matched
        path = normalized if subs else path
    if not subs:
        path, subs = RE_WIN_MOUNT.subn(_to_unix_mount, path)
    if not subs:
        path = RE_WIN_DRIVE.sub(partial(_to_unix_drive, cygdrive=cygdrive), path)

    return _resolve_path(path, posixpath.sep)


def _nt_normpath(path: str) -> str:
    norm = ntpath.normpath(path)
    if path[-1] in "/\\":
        norm += ntpath.sep
    return norm


def _get_RE_WIN_ROOT(root: str) -> re.Pattern:
    root = _nt_normpath(root)
    root = re.escape(root)
    root = re.sub(r"[/\\]+", r"[/\\]+", root)
    return re.compile(
        rf"""
        ^
        {root}[/\\]+Library
        (?P<path>[/\\].*)?
        $
        """,
        flags=re.VERBOSE,
    )


def _to_unix_root(match: re.Match) -> str:
    return match.group("path") or "/"


RE_WIN_MOUNT = re.compile(
    r"""
    ^
    [/\\]{2}(
        (?P<mount>[^/\\]+)
        (?P<path>.*)?
    )?
    $
    """,
    flags=re.VERBOSE,
)


def _to_unix_mount(match: re.Match) -> str:
    mount = match.group("mount") or ""
    path = match.group("path") or ""
    return f"//{mount}{path}"


RE_WIN_DRIVE = re.compile(
    r"""
    ^
    (?P<drive>[A-Za-z]):
    (?P<path>[/\\]+.*)?
    $
    """,
    flags=re.VERBOSE,
)


def _to_unix_drive(match: re.Match, cygdrive: bool) -> str:
    drive = match.group("drive").lower()
    path = match.group("path") or ""
    return f"{'/cygdrive' if cygdrive else ''}/{drive}{path}"


deprecated.constant(
    "25.3",
    "25.9",
    "RE_UNIX",
    re.compile(
        r"""
        (?P<drive>[A-Za-z]:)?
        (?P<path>[\/\\]+(?:[^:*?\"<>|;]+[\/\\]*)*)
        """,
        flags=re.VERBOSE,
    ),
    addendum="Use `conda.common.path._cygpath.RE_WIN_DRIVE` instead.",
)


@deprecated(
    "25.3",
    "25.9",
    addendum="Use `conda.common.path._cygpath._to_unix_drive` instead.",
)
def translate_unix(match: re.Match) -> str:
    return "/" + (
        ((match.group("drive") or "").lower() + match.group("path"))
        .replace("\\", "/")
        .replace(":", "")  # remove drive letter delimiter
        .replace("//", "/")
        .rstrip("/")
    )


def posix_to_nt(path: str, root: str, cygdrive: bool = False) -> str:
    # cygdrive is unused, but it's passed in to keep the signature consistent with nt_to_posix

    if posixpath.pathsep in path:
        return ntpath.pathsep.join(
            posix_to_nt(path, root) for path in path.split(posixpath.pathsep)
        )

    # Reverting a Unix path means unpicking MSYS2/Cygwin
    # conventions -- in order!
    # 1. drive letter forms:
    #      /x/drive (MSYS2)
    #      /cygdrive/x/drive (Cygwin)
    #    → X:\drive
    # 2. mount forms:
    #      //mount
    #    → \\mount
    # 3. root filesystem forms:
    #      /root
    #    → {root}\Library\root
    # 3. anything else

    # continue performing substitutions until a match is found
    path, subs = RE_UNIX_DRIVE.subn(_to_win_drive, path)
    if not subs:
        path, subs = RE_UNIX_MOUNT.subn(_to_win_mount, path)
    if not subs:
        path = RE_UNIX_ROOT.sub(partial(_to_win_root, root=root), path)

    return _resolve_path(path, ntpath.sep)


RE_UNIX_DRIVE = re.compile(
    r"""
    ^
    (/cygdrive)?
    /(?P<drive>[A-Za-z])
    (/+(?P<path>.*)?)?
    $
    """,
    flags=re.VERBOSE,
)


def _to_win_drive(match: re.Match) -> str:
    drive = match.group("drive").upper()
    path = match.group("path") or ""
    return f"{drive}:\\{path}"


deprecated.constant(
    "25.3",
    "25.9",
    "RE_DRIVE",
    RE_UNIX_DRIVE,
    addendum="Use `conda.common.path._cygpath.RE_UNIX_DRIVE` instead.",
)
deprecated.constant(
    "25.3",
    "25.9",
    "translation_drive",
    _to_win_drive,
    addendum="Use `conda.common.path._cygpath._to_win_drive` instead.",
)


RE_UNIX_MOUNT = re.compile(
    r"""
    ^
    /{2}(
        (?P<mount>[^/]+)
        (?P<path>/+.*)?
    )?
    $
    """,
    flags=re.VERBOSE,
)


def _to_win_mount(match: re.Match) -> str:
    mount = match.group("mount") or ""
    path = match.group("path") or ""
    return f"\\\\{mount}{path}"


deprecated.constant(
    "25.3",
    "25.9",
    "RE_MOUNT",
    RE_UNIX_MOUNT,
    addendum="Use `conda.common.path._cygpath.RE_UNIX_MOUNT` instead.",
)
deprecated.constant(
    "25.3",
    "25.9",
    "translation_mount",
    _to_win_mount,
    addendum="Use `conda.common.path._cygpath._to_win_mount` instead.",
)


RE_UNIX_ROOT = re.compile(
    r"""
    ^
    (?P<path>/.*)
    $
    """,
    flags=re.VERBOSE,
)


def _to_win_root(match: re.Match, root: str) -> str:
    path = match.group("path")
    return f"{root}\\Library{path}"


deprecated.constant(
    "25.3",
    "25.9",
    "RE_ROOT",
    RE_UNIX_ROOT,
    addendum="Use `conda.common.path._cygpath.RE_UNIX_ROOT` instead.",
)
deprecated.constant(
    "25.3",
    "25.9",
    "translation_root",
    _to_win_root,
    addendum="Use `conda.common.path._cygpath._to_win_root` instead.",
)


def _resolve_path(path: str, sep: str) -> str:
    leading = ""
    if match := re.match(r"^([/\\]+)(.*)$", path):
        leading, path = match.groups()
    return re.sub(r"[/\\]", re.escape(sep), leading) + re.sub(
        r"[/\\]+", re.escape(sep), path
    )


def resolve_paths(paths: str, pathsep: str, sep: str) -> str:
    return pathsep.join(_resolve_path(path, sep) for path in paths.split(pathsep))
