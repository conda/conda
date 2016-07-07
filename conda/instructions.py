from __future__ import absolute_import, division, print_function

from logging import getLogger

from .config import root_dir
from .exceptions import InvalidInstruction
from .fetch import fetch_pkg
from .install import (is_extracted, messages, extract, rm_extracted, rm_fetched, LINK_HARD,
                      link, unlink, symlink_conda, name_dist)
from os import access, W_OK, makedirs
from os.path import join, isdir
from .exceptions import CondaFileIOError, CondaIOError

from .install import load_meta
from blessings import Terminal
from ._vendor.progressive.bar import Bar
from ._vendor.progressive.tree import ProgressTree, Value, BarDescriptor


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


update_bar = {}
bar_length = 100
def PREFIX_CMD(state, arg):
    state['prefix'] = arg


def PRINT_CMD(state, arg):
    getLogger('print').info(arg)


def FETCH_CMD(state, arg):
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
    "Return tuple(dist, linktype)"
    parts = arg.split()
    return (parts[0], int(LINK_HARD if len(parts) < 2 else parts[1]))


def LINK_CMD(state, arg):
    dist, lt = split_linkarg(arg)
    link(state['prefix'], dist, lt, index=state['index'])


def UNLINK_CMD(state, arg):
    unlink(state['prefix'], arg)


def SYMLINK_CONDA_CMD(state, arg):
    symlink_conda(state['prefix'], arg)

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

    checked = False
    downloaded = False
    to_download = []
    for instruction, arg in plan:

        log.debug(' %s(%r)' % (instruction, arg))

        if state['i'] is not None and instruction in progress_cmds:
            state['i'] += 1
            getLogger('progress.update').info((name_dist(arg),
                                               state['i'] - 1))
        cmd = _commands.get(instruction)

        if cmd is None:
            raise InvalidInstruction(instruction)

        # check before link and unlink package
        if cmd in [LINK_CMD, UNLINK_CMD] and not checked:
            check_link_unlink(state, plan)
            checked = True

        # a hack to current implementation
        if cmd == FETCH_CMD:
            to_download.append(arg)
            continue

        if cmd == EXTRACT_CMD and not downloaded:
            parallel_download(state, to_download)
            downloaded = True
            PRINT_CMD(state, "Extracting packages ...")

        cmd(state, arg)

        if (state['i'] is not None and instruction in progress_cmds and
                state['maxval'] == state['i']):
            state['i'] = None
            getLogger('progress.stop').info(None)

    messages(state['prefix'])


def parallel_download(state, arg_list):
    try:
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(10)
    except (ImportError, RuntimeError):
        for arg in arg_list:
            FETCH_CMD(state, arg)
    else:

        bd_defaults = dict(type=Bar, kwargs=dict(max_value=bar_length))
        general_label = "Fetching Packages "
        general_label, new_arg_list = pretty_label(general_label, arg_list)
        test_d = {general_label: {}}
        leaf_values = {}
        for arg in new_arg_list:
            url = state['index'][arg.strip() + '.tar.bz2'].get('url')
            leaf_values[url] = Value(0)
            test_d[general_label][arg] = BarDescriptor(value=leaf_values[url], **bd_defaults)
            update_bar[url] = Value(0)

        t = Terminal()
        # Initialize a ProgressTree instance
        n = ProgressTree(term=t)
        # We'll use the make_room method to make sure the terminal
        #   is filled out with all the room we need
        n.make_room(test_d)
        from threading import Thread
        th = Thread(target=download_job, args=(state, arg_list, executor))
        th.start()
        while not all(leaf_values[val].value == bar_length for val in leaf_values):
            n.cursor.restore()
            for val in leaf_values:
                leaf_values[val].value = update_bar[val].value
            n.draw(test_d, BarDescriptor(bd_defaults))
        th.join()


def pretty_label(general_label, arg_list):
    max_length = len(general_label)
    for arg in arg_list:
        if len(arg) > max_length:
            max_length = len(arg)
    max_length += 2
    general_label += "".join([" "] * (max_length - len(general_label)))
    new_list = []
    for arg in arg_list:
        new_list.append(arg + str("".join([" "] * (max_length - len(arg)))))

    return general_label, new_list

def get_link_package(plan):
    link_list = []
    for instruction, arg in plan:
        if instruction == LINK:
            link_list.append(arg)
    return link_list


def get_unlink_package(plan):
    unlink_list = []
    for instruction, arg in plan:
        if instruction == UNLINK:
            unlink_list.append(arg)
    return unlink_list


def check_link_unlink(state, plan):

    unlink_list = get_unlink_package(plan)

    # check for permission
    # the folder may not exist now, just check whether can write to prefix
    prefix = state['prefix']
    if not isdir(prefix):
        try:
            makedirs(prefix)
        except IOError:
            raise CondaIOError("Could not create directory for {0}".format(prefix))

    w_permission = access(prefix, W_OK)

    if not w_permission:
        raise CondaFileIOError(prefix)

    for dist in unlink_list:

        meta = load_meta(prefix, dist)
        for f in meta['files']:
            dst = join(prefix, f)
            w_permission = access(dst, W_OK)
            if not w_permission:
                raise CondaFileIOError(dst)


def download_job(state, arg_list, executor):
    try:
        for arg in arg_list:
            executor.submit(FETCH_CMD, state, arg)
    finally:
        executor.shutdown(wait=True)
        from .install import package_cache
        for arg in arg_list:
             assert arg in package_cache()


