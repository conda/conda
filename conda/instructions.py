from __future__ import absolute_import, division, print_function

from conda.models.dist import Dist
from logging import getLogger

from .base.context import context
from conda.core.package_cache import fetch_pkg, is_extracted, extract, rm_extracted, rm_fetched
from .install import (LINK_HARD, link, messages, symlink_conda, unlink)


log = getLogger(__name__)

# op codes
CHECK_FETCH = 'CHECK_FETCH'
FETCH = 'FETCH'
CHECK_EXTRACT = 'CHECK_EXTRACT'
EXTRACT = 'EXTRACT'
CHECK_LINK= 'CHECK_LINK'
CHECK_UNLINK= 'CHECK_UNLINK'
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
    CHECK_FETCH,
    FETCH,
    CHECK_EXTRACT,
    EXTRACT,
    CHECK_LINK,
    CHECK_UNLINK,
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
    assert isinstance(arg, Dist)
    fetch_pkg(state['index'][arg])


def PROGRESS_CMD(state, arg):
    state['i'] = 0
    state['maxval'] = int(arg)
    getLogger('progress.start').info(state['maxval'])


def EXTRACT_CMD(state, arg):
    assert isinstance(arg, Dist)
    if not is_extracted(arg):
        extract(arg)


def RM_EXTRACTED_CMD(state, arg):
    assert isinstance(arg, Dist)
    rm_extracted(arg)


def RM_FETCHED_CMD(state, arg):
    assert isinstance(arg, Dist)
    rm_fetched(arg)


def split_linkarg(arg):
    """Return tuple(dist, linktype)"""
    parts = arg.split()
    return (parts[0], int(LINK_HARD if len(parts) < 2 else parts[1]))


def LINK_CMD(state, arg):
    dist, lt = split_linkarg(arg)
    dist = Dist(dist)
    log.debug("=======> LINKING %s <=======", dist)
    link(state['prefix'], dist, lt, index=state['index'])


def UNLINK_CMD(state, arg):
    log.debug("=======> UNLINKING %s <=======", arg)
    dist = Dist(arg)
    unlink(state['prefix'], dist)


def SYMLINK_CONDA_CMD(state, arg):
    symlink_conda(state['prefix'], arg)


def get_package(plan, instruction):
    """
        get the package list based on command
    :param plan: the plan for action
    :param instruction : the command
    :return:
    """
    link_list = []
    for inst, arg in plan:
        if inst == instruction:
            link_list.append(arg)
    return link_list


def check_prefix(prefix):
    assert isdir(prefix), "prefix is not exist {0}".format(prefix)
    check_write_permission(prefix)


def check_dir_exists(dst):
    return os.path.isdir(os.path.dirname(dst))


def CHECK_LINK_CMD(state, plan):
    """
        check permission issue before link and unlink
    :param state: the state of plan
    :param plan: the plan from action
    :return: the result of permission checking
    """
    link_list = get_package(plan, LINK)
    prefix = state['prefix']
    check_prefix(prefix)

    for arg in link_list:
        dist, lt = split_linkarg(arg)
        source_dir = is_extracted(dist)
        assert source_dir is not None
        info_dir = join(source_dir, 'info')
        files = list(yield_lines(join(info_dir, 'files')))
        # check write permission for every file
        for f in files:
            dst = join(prefix, f)
            check_dir_exists(dst)
            check_write_permission(dst)


def CHECK_UNLINK_CMD(state, plan):
    """
        check permission issue before link and unlink
    :param state: the state of plan
    :param plan: the plan from action
    :return: the result of permission checking
    """
    unlink_list = get_package(plan, UNLINK)
    prefix = state['prefix']
    check_prefix(prefix)

    for dist in unlink_list:
        meta = load_meta(prefix, dist)
        for f in meta['files']:
            dst = join(prefix, f)
            # make sure the dst is something
            if islink(dst) or isfile(dst) or isdir(dst):
                if islink(dst):
                    check_write_permission(os.readlink(dst))
                check_write_permission(dst)


def check_write_permission(path):
    """
        Check write permission for path
        If path not exist, go up and check for that path
    Args:
        path: the path to check permission

    Returns: True : able to write
             False : unable to write
    """
    while not exists(path):
        path = dirname(path)

    w_permission = os.access(path, W_OK)
    if not w_permission:
        raise CondaFileIOError(path, "Cannot write to path %s" % path)
    return True


def get_free_space(dir_name):
    """
        Return folder/drive free space (in bytes).
    :param dir_name: the dir name need to check
    :return: amount of free space
    """
    if on_win:
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(dir_name), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        st = os.statvfs(dir_name)
        return st.f_bavail * st.f_frsize


def check_size(path, size):
    """
        check whether the directory has enough space
    :param path:    the directory to check
    :param size:    whether has that size
    :return:    True or False
    """
    free = get_free_space(path)
    if free < size:
        raise CondaIOError("Not enough space in {}".format(path))


def CHECK_DOWNLOAD_SPACE_CMD(state, plan):
    """
        Check whether there is enough space for download packages
    :param state: the state of plan
    :param plan: the plan for the action
    :return:
    """
    arg_list = get_package(plan, FETCH)
    size = 0
    for arg in arg_list:
        if 'size' in state['index'][arg + '.tar.bz2']:
            size += state['index'][arg + '.tar.bz2']['size']

    prefix = state['prefix']
    assert isdir(prefix)
    check_size(prefix, size)


def CHECK_EXTRACT_SPACE_CMD(state, plan):
    """
        check whether there is enough space for extract packages
    :param plan: the plan for the action
    :param state : the state of plan
    :return:
    """
    arg_list = get_package(plan, EXTRACT)
    size = 0
    for arg in arg_list:
        from .install import package_cache
        rec = package_cache()[arg]
        fname = rec['files'][0]
        with tarfile.open(fname) as t:
            for m in t.getmembers():
                size += m.size

    prefix = state['prefix']
    assert isdir(prefix)
    check_size(prefix, size)


# Map instruction to command (a python function)
commands = {
    PREFIX: PREFIX_CMD,
    PRINT: PRINT_CMD,
    CHECK_FETCH: CHECK_DOWNLOAD_SPACE_CMD,
    FETCH: FETCH_CMD,
    PROGRESS: PROGRESS_CMD,
    CHECK_EXTRACT: CHECK_EXTRACT_SPACE_CMD,
    EXTRACT: EXTRACT_CMD,
    RM_EXTRACTED: RM_EXTRACTED_CMD,
    RM_FETCHED: RM_FETCHED_CMD,
    CHECK_LINK: CHECK_LINK_CMD,
    LINK: LINK_CMD,
    CHECK_UNLINK: CHECK_UNLINK_CMD,
    UNLINK: UNLINK_CMD,
    SYMLINK_CONDA: SYMLINK_CONDA_CMD,
}


def execute_instructions(plan, index=None, verbose=False, _commands=None):
    """Execute the instructions in the plan

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

    log.debug("executing plan %s", plan)

    state = {'i': None, 'prefix': context.root_dir, 'index': index}

    for instruction, arg in plan:

        log.debug(' %s(%r)', instruction, arg)

        if state['i'] is not None and instruction in progress_cmds:
            state['i'] += 1
            getLogger('progress.update').info((Dist(arg).dist_name,
                                               state['i'] - 1))
        cmd = _commands[instruction]

        # check commands require the plan
        if 'CHECK' in instruction:
            cmd(state, plan)
        else:
            cmd(state, arg)

        if (state['i'] is not None and instruction in progress_cmds and
                state['maxval'] == state['i']):

            state['i'] = None
            getLogger('progress.stop').info(None)

    messages(state['prefix'])
