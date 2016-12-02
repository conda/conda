from __future__ import absolute_import, division, print_function

from conda.install import symlink_conda
import ctypes
from logging import getLogger
import os
from os.path import isdir, isfile, islink, join
import tarfile

from .base.constants import LinkType
from .base.context import context
from .core.link import UnlinkLinkTransaction
from .core.package_cache import extract, fetch_pkg, is_extracted, rm_extracted, rm_fetched
from .exceptions import CondaFileIOError, CondaIOError
from .models.dist import Dist
from .utils import on_win

try:
    from cytoolz.itertoolz import groupby
except ImportError:
    from ._vendor.toolz.itertoolz import groupby  # NOQA


log = getLogger(__name__)

# op codes
CHECK_FETCH = 'CHECK_FETCH'
FETCH = 'FETCH'
CHECK_EXTRACT = 'CHECK_EXTRACT'
EXTRACT = 'EXTRACT'
RM_EXTRACTED = 'RM_EXTRACTED'
RM_FETCHED = 'RM_FETCHED'
PREFIX = 'PREFIX'
PRINT = 'PRINT'
PROGRESS = 'PROGRESS'
SYMLINK_CONDA = 'SYMLINK_CONDA'
UNLINK = 'UNLINK'
LINK = 'LINK'
UNLINKLINKTRANSACTION = 'UNLINKLINKTRANSACTION'

progress_cmds = set([EXTRACT, RM_EXTRACTED])
action_codes = (
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


def PREFIX_CMD(state, arg):
    state['prefix'] = arg


def PRINT_CMD(state, arg):
    if arg.startswith(('Unlinking packages', 'Linking packages')):
        return
    getLogger('print').info(arg)


def FETCH_CMD(state, arg):
    dist = Dist(arg)
    fetch_pkg(state['index'][dist])


def PROGRESS_CMD(state, arg):
    state['i'] = 0
    state['maxval'] = int(arg)
    getLogger('progress.start').info(state['maxval'])


def EXTRACT_CMD(state, arg):
    dist = Dist(arg)
    if not is_extracted(dist):
        extract(dist)


def RM_EXTRACTED_CMD(state, arg):
    dist = Dist(arg)
    rm_extracted(dist)


def RM_FETCHED_CMD(state, arg):
    dist = Dist(arg)
    rm_fetched(dist)


def split_linkarg(arg):
    """Return tuple(dist, linktype)"""
    parts = arg.split()
    return (parts[0], int(LinkType.hardlink if len(parts) < 2 else parts[1]))


# def LINK_CMD(state, arg):
#     dist, lt = split_linkarg(arg)
#     dist, lt = Dist(dist), LinkType(lt)
#     log.debug("=======> LINKING %s <=======", dist)
#     installer = get_package_installer(state['prefix'], state['index'], dist)
#     installer.link(lt)
#
#
# def UNLINK_CMD(state, arg):
#     log.debug("=======> UNLINKING %s <=======", arg)
#     dist = Dist(arg)
#     PackageUninstaller(state['prefix'], dist).unlink()


def SYMLINK_CONDA_CMD(state, arg):
    symlink_conda(state['prefix'], arg)


def UNLINKLINKTRANSACTION_CMD(state, arg):
    unlink_dists, link_dists = arg
    txn = UnlinkLinkTransaction.create_from_dists(state['index'], state['prefix'],
                                                  unlink_dists, link_dists)
    txn.execute()


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


# def get_unlink_files(plan, prefix):
#     unlink_list = get_package(plan, UNLINK)
#     unlink_files = []
#     for dist in unlink_list:
#         meta = load_meta(prefix, dist)
#         if meta is not None:
#             unlink_files.extend(meta)
#     return unlink_files


def check_files_in_package(source_dir, files):
    for f in files:
        source_file = join(source_dir, f)
        if isfile(source_file) or islink(source_file):
            return True
        else:
            raise CondaFileIOError(source_file, "File %s does not exist in tarball" % f)


# def CHECK_LINK_CMD(state, plan):
#     """
#         check permission issue before link and unlink
#     :param state: the state of plan
#     :param plan: the plan from action
#     :return: the result of permission checking
#     """
#     link_list = get_package(plan, LINK)
#     prefix = state['prefix']
#     unlink_files = get_unlink_files(plan, prefix)
#     file_permissions = FilePermissions(prefix)
#
#     for arg in link_list:
#         dist, lt = split_linkarg(arg)
#         source_dir = is_extracted(Dist(dist))
#         assert source_dir is not None
#         info_dir = join(source_dir, 'info')
#         files = list(yield_lines(join(info_dir, 'files')))
#         check_files_in_package(source_dir, files)
#         file_permissions.check(files, unlink_files)


# def CHECK_UNLINK_CMD(state, plan):
#     """
#         check permission issue before link and unlink
#     :param state: the state of plan
#     :param plan: the plan from action
#     :return: the result of permission checking
#     """
#     unlink_list = get_package(plan, UNLINK)
#     prefix = state['prefix']
#     file_permissions = FilePermissions(prefix)
#
#     for dist in unlink_list:
#         meta = load_meta(prefix, dist)
#         for f in meta['files']:
#             dst = join(prefix, f)
#             # make sure the dst is something
#             if islink(dst) or isfile(dst) or isdir(dst):
#                 if islink(dst):
#                     sym_path = os.path.normpath(join(os.path.dirname(dst), os.readlink(dst)))
#                     file_permissions.check_write_permission(sym_path)
#                 file_permissions.check_write_permission(dst)


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
        if 'size' in state['index'][arg]:
            size += state['index'][arg]['size']

    prefix = state['prefix']
    assert os.path.isdir(prefix)
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
    UNLINK: None,
    LINK: None,
    SYMLINK_CONDA: SYMLINK_CONDA_CMD,
    UNLINKLINKTRANSACTION: UNLINKLINKTRANSACTION_CMD,
}


OP_ORDER = (CHECK_FETCH,
            RM_FETCHED,
            FETCH,
            CHECK_EXTRACT,
            RM_EXTRACTED,
            EXTRACT,
            UNLINK,
            LINK,
            )


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

    # pull out unlink and link commands for the transaction
    grouped_instructions = groupby(lambda x: x[0], plan)
    unlink_dists = tuple(Dist(d[1]) for d in grouped_instructions.get(UNLINK, ()))
    link_dists = tuple(Dist(d[1].split(' ', 1)[0]) for d in grouped_instructions.get(LINK, ()))

    first_unlink_link_idx = next((q for q, p in enumerate(plan) if p[0] in (UNLINK, LINK)), -1)
    if first_unlink_link_idx >= 0:
        plan.insert(first_unlink_link_idx, (UNLINKLINKTRANSACTION, (unlink_dists, link_dists)))
        plan = [p for p in plan if p[0] not in (UNLINK, LINK)]  # filter out unlink/link

    state = {'i': None, 'prefix': context.root_dir, 'index': index}

    for instruction, arg in plan:

        log.debug(' %s(%r)', instruction, arg)

        if state['i'] is not None and instruction in progress_cmds:
            state['i'] += 1
            getLogger('progress.update').info((Dist(arg).dist_name,
                                               state['i'] - 1))
        cmd = _commands[instruction]

        cmd(state, arg)

        if (state['i'] is not None and instruction in progress_cmds and
                state['maxval'] == state['i']):

            state['i'] = None
            getLogger('progress.stop').info(None)
