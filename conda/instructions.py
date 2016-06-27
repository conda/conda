from __future__ import absolute_import, division, print_function

from logging import getLogger

from .config import root_dir
from .exceptions import InvalidInstruction
from .fetch import fetch_pkg
from .install import (is_extracted, messages, extract, rm_extracted, rm_fetched, LINK_HARD,
                      link, unlink, symlink_conda)
from .utils import find_parent_shell
import click

log = getLogger(__name__)

# op codes
FETCH = 'FETCH'
EXTRACT = 'EXTRACT'
UNLINK = 'UNLINK'
LINK = 'LINK'
RM_EXTRACTED = 'RM_EXTRACTED'
RM_FETCHED = 'RM_FETCHED'
PREFIX = 'PREFIX'
PRINT = 'PRINT'
PROGRESS = 'PROGRESS'
SYMLINK_CONDA = 'SYMLINK_CONDA'

progress_cmds = set([FETCH, RM_FETCHED, EXTRACT, RM_EXTRACTED, LINK, UNLINK])

action_codes = (
    FETCH,
    EXTRACT,
    UNLINK,
    LINK,
    SYMLINK_CONDA,
    RM_EXTRACTED,
    RM_FETCHED,
)


def PREFIX_CMD(state, arg):
    state['prefix'] = arg


def FETCH_CMD(state, arg):
    fetch_pkg(state['index'][arg + '.tar.bz2'])


def EXTRACT_CMD(state, arg):
    if not is_extracted(arg):
        extract(arg)


def RM_EXTRACTED_CMD(state, arg):
    rm_extracted(arg)


def RM_FETCHED_CMD(state, arg):
    rm_fetched(arg)


def split_linkarg(arg):
    "Return tuple(dist, linktype, shortcuts)"
    parts = arg.split()
    return (parts[0], int(LINK_HARD if len(parts) < 2 else parts[1]),
            False if len(parts) < 3 else parts[2] == 'True')


def LINK_CMD(state, arg):
    dist, lt, shortcuts = split_linkarg(arg)
    link(state['prefix'], dist, lt, index=state['index'], shortcuts=shortcuts)


def UNLINK_CMD(state, arg):
    unlink(state['prefix'], arg)


def SYMLINK_CONDA_CMD(state, arg):
    symlink_conda(state['prefix'], arg, find_parent_shell(path=False))

# Map instruction to command (a python function)
commands = {
    PREFIX: PREFIX_CMD,
    FETCH: FETCH_CMD,
    EXTRACT: EXTRACT_CMD,
    RM_EXTRACTED: RM_EXTRACTED_CMD,
    RM_FETCHED: RM_FETCHED_CMD,
    LINK: LINK_CMD,
    UNLINK: UNLINK_CMD,
    SYMLINK_CONDA: SYMLINK_CONDA_CMD,
}

action_message = {
    FETCH_CMD: "[ Downloading Packages   ",
    RM_FETCHED_CMD: "[ Remove Downloaded Packages   ",
    EXTRACT_CMD: "[ Extracting Packages    ",
    RM_EXTRACTED_CMD: "[ RM Extracting Packages ",
    LINK_CMD: "[ Linking Packages       ",
    UNLINK_CMD: "[ Unlinking Packages     "
}


def execute_instructions(plan, index=None, verbose=False, _commands=None):
    """
    Execute the instructions in the plan

    :param plan: A list of (instruction, arg) tuples
    :param index: The meta-data index
    :param verbose: verbose output
    :param _commands: (For testing only) dict mapping an instruction to executable if None
    then the default commands will be used
    """
    if _commands is None:
        _commands = commands

    if verbose:
        from .console import setup_verbose_handlers
        setup_verbose_handlers()
    state = {'i': None, 'prefix': root_dir, 'index': index}

    """
        iterate through actions in plan
        If can be done in parallel, go to package_multithread_cmd
        Otherwise, done in serial
    """
    for instruction, arg in plan.items():
        log.debug(' %s(%r)' % (instruction, arg))
        cmd = _commands.get(instruction)

        if cmd is None:
            raise InvalidInstruction(instruction)
        arg = [arg] if not isinstance(arg, list) else arg

        # Done in serial
        if instruction in progress_cmds:
            if cmd == PREFIX_CMD:
                cmd(state, arg[0])
            else:
                label = action_message[cmd] + " ]" if \
                    cmd in action_message else str(cmd)
                with click.progressbar(arg, label=label) as bar:
                    for ar in bar:
                        cmd(state, ar)
            continue
        # Normal execution
        for ar in arg:
            cmd(state, ar)

    messages(state['prefix'])
