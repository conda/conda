# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Define the instruction set (constants) for conda operations."""

from logging import getLogger
from os.path import isfile, join

from .common.io import time_recorder
from .core.link import UnlinkLinkTransaction
from .core.package_cache_data import ProgressiveFetchExtract
from .deprecations import deprecated
from .exceptions import CondaFileIOError
from .gateways.disk.link import islink

log = getLogger(__name__)

# op codes
CHECK_FETCH = "CHECK_FETCH"
FETCH = "FETCH"
CHECK_EXTRACT = "CHECK_EXTRACT"
EXTRACT = "EXTRACT"
RM_EXTRACTED = "RM_EXTRACTED"
RM_FETCHED = "RM_FETCHED"
deprecated.constant("24.9", "25.3", "PREFIX", "PREFIX")
PRINT = "PRINT"
PROGRESS = "PROGRESS"
SYMLINK_CONDA = "SYMLINK_CONDA"
UNLINK = "UNLINK"
LINK = "LINK"
UNLINKLINKTRANSACTION = "UNLINKLINKTRANSACTION"
PROGRESSIVEFETCHEXTRACT = "PROGRESSIVEFETCHEXTRACT"


PROGRESS_COMMANDS = {EXTRACT, RM_EXTRACTED}
ACTION_CODES = (
    CHECK_FETCH,
    FETCH,
    CHECK_EXTRACT,
    EXTRACT,
    UNLINK,
    LINK,
    SYMLINK_CONDA,
    RM_EXTRACTED,
    RM_FETCHED,
)


def PRINT_CMD(state, arg):  # pragma: no cover
    if arg.startswith(("Unlinking packages", "Linking packages")):
        return
    getLogger("conda.stdout.verbose").info(arg)


def FETCH_CMD(state, package_cache_entry):
    raise NotImplementedError()


def EXTRACT_CMD(state, arg):
    raise NotImplementedError()


def PROGRESSIVEFETCHEXTRACT_CMD(state, progressive_fetch_extract):  # pragma: no cover
    assert isinstance(progressive_fetch_extract, ProgressiveFetchExtract)
    progressive_fetch_extract.execute()


def UNLINKLINKTRANSACTION_CMD(state, arg):  # pragma: no cover
    unlink_link_transaction = arg
    assert isinstance(unlink_link_transaction, UnlinkLinkTransaction)
    unlink_link_transaction.execute()


def check_files_in_package(source_dir, files):
    for f in files:
        source_file = join(source_dir, f)
        if isfile(source_file) or islink(source_file):
            return True
        else:
            raise CondaFileIOError(source_file, "File %s does not exist in tarball" % f)


# Map instruction to command (a python function)
commands = {
    PRINT: PRINT_CMD,
    FETCH: FETCH_CMD,
    PROGRESS: lambda x, y: None,
    EXTRACT: EXTRACT_CMD,
    RM_EXTRACTED: lambda x, y: None,
    RM_FETCHED: lambda x, y: None,
    UNLINK: None,
    LINK: None,
    SYMLINK_CONDA: lambda x, y: None,
    UNLINKLINKTRANSACTION: UNLINKLINKTRANSACTION_CMD,
    PROGRESSIVEFETCHEXTRACT: PROGRESSIVEFETCHEXTRACT_CMD,
}


OP_ORDER = (
    RM_FETCHED,
    FETCH,
    RM_EXTRACTED,
    EXTRACT,
    UNLINK,
    LINK,
)


@time_recorder("execute_plan")
def execute_plan(old_plan, index=None, verbose=False):  # pragma: no cover
    plan = _update_old_plan(old_plan)
    execute_instructions(plan, index, verbose)


def execute_instructions(
    plan, index=None, verbose=False, _commands=None
):  # pragma: no cover
    """Execute the instructions in the plan

    :param plan: A list of (instruction, arg) tuples
    :param index: The meta-data index
    :param verbose: verbose output
    :param _commands: (For testing only) dict mapping an instruction to executable if None
    then the default commands will be used
    """
    from .base.context import context
    from .instructions import PROGRESS_COMMANDS, commands
    from .models.dist import Dist

    if _commands is None:
        _commands = commands

    log.debug("executing plan %s", plan)

    state = {"i": None, "prefix": context.root_prefix, "index": index}

    for instruction, arg in plan:
        log.debug(" %s(%r)", instruction, arg)

        if state["i"] is not None and instruction in PROGRESS_COMMANDS:
            state["i"] += 1
            getLogger("progress.update").info((Dist(arg).dist_name, state["i"] - 1))
        cmd = _commands[instruction]

        if callable(cmd):
            cmd(state, arg)

        if (
            state["i"] is not None
            and instruction in PROGRESS_COMMANDS
            and state["maxval"] == state["i"]
        ):
            state["i"] = None
            getLogger("progress.stop").info(None)


def _update_old_plan(old_plan):  # pragma: no cover
    """
    Update an old plan object to work with
    `conda.instructions.execute_instructions`
    """
    plan = []
    for line in old_plan:
        if line.startswith("#"):
            continue
        if " " not in line:
            from .exceptions import ArgumentError

            raise ArgumentError(f"The instruction {line!r} takes at least one argument")

        instruction, arg = line.split(" ", 1)
        plan.append((instruction, arg))
    return plan
