from logging import getLogger
import re

from conda import config
from conda import install
from conda.utils import find_parent_shell
from conda.exceptions import InvalidInstruction
from conda.fetch import fetch_pkg


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


def fetch(index, dist):
    assert index is not None
    fn = dist + '.tar.bz2'
    fetch_pkg(index[fn])


def FETCH_CMD(state, arg):
    fetch(state['index'], arg)


def PROGRESS_CMD(state, arg):
    state['i'] = 0
    state['maxval'] = int(arg)
    getLogger('progress.start').info(state['maxval'])


def EXTRACT_CMD(state, arg):
    if not install.is_extracted(config.pkgs_dirs[0], arg):
        install.extract(config.pkgs_dirs[0], arg)


def RM_EXTRACTED_CMD(state, arg):
    install.rm_extracted(config.pkgs_dirs[0], arg)


def RM_FETCHED_CMD(state, arg):
    install.rm_fetched(config.pkgs_dirs[0], arg)


def split_linkarg(arg):
    "Return tuple(dist, pkgs_dir, linktype)"
    pat = re.compile(r'\s*(\S+)(?:\s+(.+?)\s+(\d+))?\s*$')
    m = pat.match(arg)
    dist, pkgs_dir, linktype = m.groups()
    if pkgs_dir is None:
        pkgs_dir = config.pkgs_dirs[0]
    if linktype is None:
        linktype = install.LINK_HARD
    return dist, pkgs_dir, int(linktype)


def link(prefix, arg, index=None):
    dist, pkgs_dir, lt = split_linkarg(arg)
    install.link(pkgs_dir, prefix, dist, lt, index=index)


def LINK_CMD(state, arg):
    link(state['prefix'], arg, index=state['index'])


def UNLINK_CMD(state, arg):
    install.unlink(state['prefix'], arg)


def SYMLINK_CONDA_CMD(state, arg):
    install.symlink_conda(state['prefix'], arg, find_parent_shell())

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
        from conda.console import setup_verbose_handlers
        setup_verbose_handlers()

    state = {'i': None, 'prefix': config.root_dir, 'index': index}

    for instruction, arg in plan:

        log.debug(' %s(%r)' % (instruction, arg))

        if state['i'] is not None and instruction in progress_cmds:
            state['i'] += 1
            getLogger('progress.update').info((install.name_dist(arg),
                state['i']-1))
        cmd = _commands.get(instruction)

        if cmd is None:
            raise InvalidInstruction(instruction)

        cmd(state, arg)

        if (state['i'] is not None and instruction in progress_cmds
                and state['maxval'] == state['i']):
            state['i'] = None
            getLogger('progress.stop').info(None)

    install.messages(state['prefix'])
