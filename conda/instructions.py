from __future__ import absolute_import, division, print_function

from logging import getLogger

from .config import root_dir
from .exceptions import InvalidInstruction
from .fetch import fetch_pkg
from .install import (is_extracted, messages, extract, rm_extracted, rm_fetched, LINK_HARD,
                      link, unlink, symlink_conda, name_dist)
from .utils import find_parent_shell


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


progress_cmds = set([EXTRACT, RM_EXTRACTED, LINK, UNLINK])
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


def PRINT_CMD(state, arg):
    getLogger('print').info(arg)


def FETCH_CMD(state, arg):
    print("fetch the index ,", arg)
    fetch_pkg(state['index'][arg + '.tar.bz2'])


def PROGRESS_CMD(state, arg):
    state['i'] = 0
    state['maxval'] = int(arg)
    getLogger('progress.start').info(state['maxval'])


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
    symlink_conda(state['prefix'], arg, find_parent_shell())

# Map instruction to command (a python function)
commands = {
    PREFIX: PREFIX_CMD,
    PRINT: PRINT_CMD,
    FETCH: FETCH_CMD,
    PROGRESS: PROGRESS_CMD,
    EXTRACT: EXTRACT_CMD,
    RM_EXTRACTED: RM_EXTRACTED_CMD,
    RM_FETCHED: RM_FETCHED_CMD,
    LINK: LINK_CMD,
    UNLINK: UNLINK_CMD,
    SYMLINK_CONDA: SYMLINK_CONDA_CMD,
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

    to_download = []
    print(plan)
    for instruction, arg in plan:

        log.debug(' %s(%r)' % (instruction, arg))

        if state['i'] is not None and instruction in progress_cmds:
            state['i'] += 1
            getLogger('progress.update').info((name_dist(arg),
                                               state['i'] - 1))
        cmd = _commands.get(instruction)

        if cmd is None:
            raise InvalidInstruction(instruction)

        # if it is fetch command
        # put that command in a list for future multi-thread processing
        if cmd == FETCH_CMD:
            to_download.append((state, arg))
            continue

        # if it is a extract command
        # start the fetch multi-thread process
        if (cmd == EXTRACT_CMD or cmd == RM_EXTRACTED_CMD) and to_download:
            print("To download", len(to_download))
            try:
                import concurrent.futures
                executor = concurrent.futures.ThreadPoolExecutor(10)
            except (ImportError, RuntimeError):
                # concurrent.futures is only available in Python >= 3.2 or if futures is installed
                # RuntimeError is thrown if number of threads are limited by OS

                for state_download, arg_download in to_download:
                    FETCH_CMD(state_download, arg_download)
                    getLogger('downloading %s ' % str(arg_download)).info(None)
                to_download = None
            else:
                try:
                    print("using multi thread")
                    tuple(executor.submit(FETCH_CMD, state_d,
                                          arg_d) for (state_d, arg_d) in to_download)
                finally:
                    executor.shutdown(wait=True)
                    to_download = None

        cmd(state, arg)

        if (state['i'] is not None and instruction in progress_cmds and
                state['maxval'] == state['i']):
            state['i'] = None
            getLogger('progress.stop').info(None)

    messages(state['prefix'])
