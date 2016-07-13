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
from collections import OrderedDict
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


progress_cmds = set([FETCH, EXTRACT, RM_EXTRACTED, LINK, UNLINK])
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
    plan_dict = new_plan(plan)
    state = {'prefix': root_dir, 'index': index}
    checked = False
    start_label = "[   START      ]"
    end_label = "[   COMPLETE   ]"
    for instruction in plan_dict:

        if '_' not in instruction and plan_dict[instruction]:
            header_message = '%sing packages ...' % instruction.capitalize()
        elif instruction.startswith('RM_'):
            header_message = 'Pruning %s packages from the cache ...' % instruction[3:].lower()
        else:
            header_message = None

        log.debug(' %s' % instruction)
        cmd = _commands.get(instruction)

        if cmd is None:
            raise InvalidInstruction(instruction)

        # check before link and unlink package
        if cmd in [LINK_CMD, UNLINK_CMD] and not checked:
            check_link_unlink(state, plan)
            checked = True

        if instruction in progress_cmds and plan_dict[instruction]:

            # print the message header
            if header_message:
                PRINT_CMD(state, header_message)
            # get the label
            label_dict = pretty_label(end_label, plan_dict[instruction])
            # execute the command
            if cmd == FETCH_CMD:
                parallel_download(state, plan_dict[instruction])
            else:
                # start a progress bar
                bar = Bar(title=start_label, max_value=bar_length, fallback=True, num_rep="percentage")
                bar.cursor.clear_lines(2)
                #   Before beginning to draw our bars, we save the position
                #   of our cursor so we can restore back to this position before writing
                #   the next time.
                bar.cursor.save()
                length = len(plan_dict[instruction])
                for i in range(len(plan_dict[instruction])+1):
                    # the end step
                    if i == len(plan_dict[instruction]):
                        bar.cursor.restore()
                        bar.update_title(end_label)
                        bar.draw(value=bar_length)
                        continue

                    # other operation
                    arg = plan_dict[instruction][i]
                    # We restore the cursor to saved position before writing
                    bar.cursor.restore()
                    # execute the command
                    cmd(state, arg)
                    # Now we draw the bar
                    bar.update_title(label_dict[arg])
                    bar.draw(value=bar_length/length * i)
        else:
            for arg in plan_dict[instruction]:
                cmd(state, arg)
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
        label_dict = pretty_label(general_label, arg_list)
        general_label = label_dict[general_label]
        test_d = {general_label: {}}
        leaf_values = {}
        for arg in arg_list:
            url = state['index'][arg + '.tar.bz2'].get('url')
            leaf_values[url] = Value(0)
            test_d[general_label][label_dict[arg]] = BarDescriptor(value=leaf_values[url], **bd_defaults)
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
    """
        Make the label and the argument looks pretty
    :param general_label: the general label for the progress bar
    :param arg_list: the list of package
    :return: the map of old packages and new label
    """
    # clean the name of packages
    new_arg_list = []
    for arg in arg_list:
        new_arg_list.append(arg.rsplit("-", 2)[0])
    res = {}

    # align all the names
    max_length = len(general_label)
    for arg in new_arg_list:
        if len(arg) > max_length:
            max_length = len(arg)
    max_length += 2
    res[general_label] = general_label + "".join([" "] * (max_length - len(general_label)))
    for arg in arg_list:
        res[arg] = arg + str("".join([" "] * (max_length - len(arg))))

    return res


def get_link_package(plan):
    """
        Get all the packages to link
    :param plan: the plan from action
    :return: the list of packages to link
    """
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


def new_plan(plan):
    plan_dict = OrderedDict()
    for instruction, arg in plan:
        if instruction == PROGRESS:
            continue
        if instruction not in plan_dict:
            plan_dict[instruction] = []
        else:
            plan_dict[instruction].append(arg)
    return plan_dict


