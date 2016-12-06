from __future__ import absolute_import, division, print_function

from conda.install import symlink_conda
import ctypes
from functools import reduce
from logging import getLogger
from operator import add
import os
from os.path import basename, isdir, isfile, islink, join
import tarfile

from .base.context import context
from .core.link import UnlinkLinkTransaction
from .core.package_cache import extract, fetch_pkg, is_extracted, rm_extracted, rm_fetched
from .exceptions import CondaFileIOError, CondaIOError
from .models.dist import Dist
from .utils import on_win

try:
    from cytoolz.itertoolz import concatv, groupby
except ImportError:
    from ._vendor.toolz.itertoolz import concatv, groupby  # NOQA


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


def SYMLINK_CONDA_CMD(state, arg):
    if basename(state['prefix']).startswith('_'):
        log.info("Conda environment at %s "
                 "start with '_'. Skipping symlinking conda.", state['prefix'])
        return
    symlink_conda(state['prefix'], arg)


def UNLINKLINKTRANSACTION_CMD(state, arg):
    unlink_dists, link_dists = arg
    txn = UnlinkLinkTransaction.create_from_dists(state['index'], state['prefix'],
                                                  unlink_dists, link_dists)
    txn.execute()


def check_files_in_package(source_dir, files):
    for f in files:
        source_file = join(source_dir, f)
        if isfile(source_file) or islink(source_file):
            return True
        else:
            raise CondaFileIOError(source_file, "File %s does not exist in tarball" % f)


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
    _, link_dists = next((p[1] for p in plan if p[0] == UNLINKLINKTRANSACTION),
                                    (None, None))
    if link_dists is None:
        return

    prefix = state['prefix']
    index = state['index']
    assert isdir(prefix)
    size = reduce(add, (index[dist].get('size', 0) for dist in link_dists), 0)
    check_size(prefix, size)


def CHECK_EXTRACT_SPACE_CMD(state, plan):
    """
        check whether there is enough space for extract packages
    :param plan: the plan for the action
    :param state : the state of plan
    :return:
    """
    _, link_dists = next((p[1] for p in plan if p[0] == UNLINKLINKTRANSACTION),
                                    (None, None))
    if link_dists is None:
        return

    def extracted_size(dist):
        from .core.package_cache import package_cache
        dist_tarball = package_cache()[dist]['files'][0]
        with tarfile.open(dist_tarball) as tar_bz2:
            return reduce(add, (m.size for m in tar_bz2.getmembers()), 0)

    size = reduce(add, (extracted_size(dist)for dist in link_dists), 0)

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


def handle_menuinst(unlink_dists, link_dists):
    if not on_win:
        return unlink_dists, link_dists

    # Always link/unlink menuinst first/last on windows in case a subsequent
    # package tries to import it to create/remove a shortcut

    # unlink
    menuinst_idx = next((q for q, d in enumerate(unlink_dists) if d.name == 'menuinst'), None)
    if menuinst_idx is not None:
        unlink_dists = tuple(concatv(
            unlink_dists[:menuinst_idx],
            unlink_dists[menuinst_idx+1:],
            unlink_dists[menuinst_idx:menuinst_idx+1],
        ))

    # link
    menuinst_idx = next((q for q, d in enumerate(link_dists) if d.name == 'menuinst'), None)
    if menuinst_idx is not None:
        link_dists = tuple(concatv(
            link_dists[menuinst_idx:menuinst_idx+1],
            link_dists[:menuinst_idx],
            link_dists[menuinst_idx+1:],
        ))

    return unlink_dists, link_dists


def inject_UNLINKLINKTRANSACTION(plan):
    first_unlink_link_idx = next((q for q, p in enumerate(plan) if p[0] in (UNLINK, LINK)), -1)
    if first_unlink_link_idx >= 0:
        grouped_instructions = groupby(lambda x: x[0], plan)
        unlink_dists = tuple(Dist(d[1]) for d in grouped_instructions.get(UNLINK, ()))
        link_dists = tuple(Dist(d[1]) for d in grouped_instructions.get(LINK, ()))
        unlink_dists, link_dists = handle_menuinst(unlink_dists, link_dists)
        plan.insert(first_unlink_link_idx, (UNLINKLINKTRANSACTION, (unlink_dists, link_dists)))
        plan = [p for p in plan if p[0] not in (UNLINK, LINK)]  # filter out unlink/link
    return plan


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
    plan = inject_UNLINKLINKTRANSACTION(plan)

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
