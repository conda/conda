# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
These helpers were originally defined in tests/test_create.py,
but were refactored here so downstream projects can benefit from
them too.
"""

from __future__ import annotations

import os
import sys
from logging import getLogger
from os.path import join
from pathlib import Path
from typing import TYPE_CHECKING

from ..common.compat import on_win
from ..common.io import dashlist
from ..core.prefix_data import PrefixData
from ..gateways.logging import DEBUG
from ..models.match_spec import MatchSpec

if TYPE_CHECKING:
    from ..models.records import PrefixRecord

TEST_LOG_LEVEL = DEBUG
PYTHON_BINARY = "python.exe" if on_win else "bin/python"
UNICODE_CHARACTERS = "ōγђ家固한áêñßôç"
# UNICODE_CHARACTERS_RESTRICTED = u"áêñßôç"
UNICODE_CHARACTERS_RESTRICTED = "abcdef"
which_or_where = "which" if not on_win else "where"
cp_or_copy = "cp" if not on_win else "copy"
env_or_set = "env" if not on_win else "set"

# UNICODE_CHARACTERS = u"12345678abcdef"
# UNICODE_CHARACTERS_RESTRICTED = UNICODE_CHARACTERS

# When testing for bugs, you may want to change this to a _,
# for example to see if a bug is related to spaces in prefixes.
SPACER_CHARACTER = " "

log = getLogger(__name__)


def escape_for_winpath(p):
    return p.replace("\\", "\\\\")


class Commands:
    COMPARE = "compare"
    CONFIG = "config"
    CLEAN = "clean"
    CREATE = "create"
    INFO = "info"
    INSTALL = "install"
    LIST = "list"
    REMOVE = "remove"
    SEARCH = "search"
    UPDATE = "update"
    RUN = "run"


def package_is_installed(
    prefix: str | os.PathLike | Path,
    spec: str | MatchSpec,
    reload_records: bool = True,
) -> PrefixRecord | None:
    spec = MatchSpec(spec)
    prefix_data = PrefixData(prefix, interoperability=True)
    if reload_records:
        prefix_data.load()
    prefix_recs = tuple(prefix_data.query(spec))
    if not prefix_recs:
        return None
    elif len(prefix_recs) > 1:
        raise AssertionError(
            f"Multiple packages installed.{dashlist(prec.dist_str() for prec in prefix_recs)}"
        )
    else:
        return prefix_recs[0]


def get_shortcut_dir(prefix_for_unix=sys.prefix):
    if sys.platform == "win32":
        # On Windows, .nonadmin has been historically created by constructor in sys.prefix
        user_mode = "user" if Path(sys.prefix, ".nonadmin").is_file() else "system"
        try:  # menuinst v2
            from menuinst.platforms.win_utils.knownfolders import dirs_src

            return dirs_src[user_mode]["start"][0]
        except ImportError:  # older menuinst versions; TODO: remove
            try:
                from menuinst.win32 import dirs_src

                return dirs_src[user_mode]["start"][0]
            except ImportError:
                from menuinst.win32 import dirs

                return dirs[user_mode]["start"]
    # on unix, .nonadmin is only created by menuinst v2 as needed on the target prefix
    # it might exist, or might not; if it doesn't, we try to create it
    # see https://github.com/conda/menuinst/issues/150
    non_admin_file = Path(prefix_for_unix, ".nonadmin")
    if non_admin_file.is_file():
        user_mode = "user"
    else:
        try:
            non_admin_file.touch()
        except OSError:
            user_mode = "system"
        else:
            user_mode = "user"
            non_admin_file.unlink()

    if sys.platform == "darwin":
        if user_mode == "user":
            return join(os.environ["HOME"], "Applications")
        return "/Applications"
    if sys.platform == "linux":
        if user_mode == "user":
            return join(os.environ["HOME"], ".local", "share", "applications")
        return "/usr/share/applications"
    raise NotImplementedError(sys.platform)
