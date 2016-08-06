from __future__ import absolute_import, division, print_function

from logging import getLogger

from .base.context import context
from .exceptions import InvalidInstruction
from .fetch import fetch_pkg
from .install import (is_extracted, messages, extract, rm_extracted, rm_fetched, LINK_HARD,
                      link, unlink, symlink_conda)
from conda._vendor.progressive.blessings import Terminal
from ._vendor.progressive.bar import Bar
from ._vendor.progressive.tree import ProgressTree, Value, BarDescriptor
from collections import OrderedDict
from .compat import itervalues
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

    # convert plan from a tuple list to a dictionary
    plan_dict = new_plan(plan)
    state = {'prefix': context.root_dir, 'index': index}
    download_label = "Fetching Packages "
    complete_label = "[   COMPLETE   ]"
    # iterate through the plan_dict
    for instruction in plan_dict:
        # get the header message for progressive command
        if '_' not in instruction and plan_dict[instruction]:
            header_message = '%sing packages ...' % instruction.capitalize()
        elif instruction.startswith('RM_'):
            header_message = 'Pruning %s packages from the cache ...' % instruction[3:].lower()
        else:
            header_message = None

        # get the command
        log.debug(' %s' % instruction)
        cmd = _commands.get(instruction)

        if cmd is None:
            raise InvalidInstruction(instruction)

        # if it is progress command, create a progress bar for that
        if instruction in progress_cmds and plan_dict[instruction]:

            # print the message header
            if header_message:
                PRINT_CMD(state, header_message)
            # now, just parallel download function
            if cmd == FETCH_CMD:
                from conda._vendor.progressive.exceptions import LengthOverflowError
                # the terminal height may not enough to show multiple progress bar
                try:
                    multi_progress(FETCH_CMD, parallel_job,
                                   plan_dict[instruction], download_label, state)
                except (LengthOverflowError, RuntimeError) as e:
                    # fail running in parallel, do in serial
                    log.debug(e)
                    single_progress(FETCH_CMD, plan_dict[instruction],
                                    download_label, state)

            else:
                single_progress(cmd, plan_dict[instruction], complete_label, state)

        else:
            # for non-progressive command, no progress bar
            for arg in plan_dict[instruction]:
                cmd(state, arg)
    messages(state['prefix'])


def pretty_label(general_label, arg_list):
    """
        Make the label and the argument looks pretty
    :param general_label: the general label for the progress bar
    :param arg_list: the list of package
    :return: the map of old packages and new label
    """
    # clean the name of packages
    new_arg_list = {}
    for arg in arg_list:
        new_arg_list[arg] = arg.rsplit("-", 2)[0]
    res = {}

    # align all the names by find the max length
    max_length = len(general_label)
    for arg in itervalues(new_arg_list):
        if len(arg) > max_length:
            max_length = len(arg)
    max_length += 2

    # padding " " at the end of each label
    res[general_label] = general_label + "".join([" "] * (max_length - len(general_label)))
    for arg in arg_list:
        res[arg] = new_arg_list[arg] + str("".join([" "] * (max_length - len(new_arg_list[arg]))))
    return res


def parallel_job(state, arg_list, executor, cmd):
    """
        Finish job in parallel
    :param state: the state of plan
    :param arg_list: the argument to download
    :param executor: the thread pool executor
    :return: None
    """
    # start the pool executor
    try:
        for arg in arg_list:
            executor.submit(cmd, state, arg)
    finally:
        executor.shutdown(wait=True)
        # check whether download is finished
        for url in update_bar:
            update_bar[url].value = bar_length
        from .install import package_cache
        for arg in arg_list:
            assert arg in package_cache()


def new_plan(plan):
    """
        Convert plan from tuple list to Ordered Dictionary
        example : [(A, 1), (A,2), (A,3), (B, 1), (C,1)]
        will return {A:[1,2,3], B:1, C:1}
    :param plan:
    :return:
    """
    plan_dict = OrderedDict()
    for instruction, arg in plan:
        if instruction in [PROGRESS, PRINT]:
            continue
        if instruction not in plan_dict:
            plan_dict[instruction] = []

        plan_dict[instruction].append(arg)
    return plan_dict


def single_progress(func, arg_list, label, state):
    """
        start a single job with one line progress bar
    :param func:  the command
    :param arg_list: the argument list
    :param label: the label for the progress bar
    :param state: state of the plan
    :return: None
    """
    import sys
    label_dict = pretty_label(label, arg_list)
    # if the program is connected to terminal
    if sys.stdout.isatty():
        # start a progress bar
        bar = Bar(title="".join([" "] * len(label_dict[label])),
                  max_value=bar_length, fallback=True, num_rep="percentage")
        bar.cursor.clear_lines(2)
        #   Before beginning to draw our bars, we save the position
        #   of our cursor so we can restore back to this position before writing
        #   the next time.
        bar.cursor.save()
        length = len(arg_list)
        for i in range(length+1):
            # the end step, show [ COMPLETE ]
            if i == length:
                bar.cursor.restore()
                bar.update_title(label_dict[label])
                bar.draw(value=bar_length)
                continue
            # normal operation
            arg = arg_list[i]
            # We restore the cursor to saved position before writing
            bar.cursor.restore()
            # Now we draw the bar
            bar.update_title(label_dict[arg])
            bar.draw(value=bar_length/length * i)
            # execute the command
            func(state, arg)
    # no terminal, no progress bar
    else:
        for arg in arg_list:
            func(state, arg)


def multi_progress(func, parallel_func,  arg_list, label, state):
    """
        start do job in parallel with multi-updated progress bar
    :param func: the original function
    :param parallel_func: paralleled function based on func
    :param arg_list: the argument list
    :param label: the label for progress bar
    :param state: the state of plan
    :return: None
    """
    # if success, parallel download, otherwise, download in serial
    try:
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(10)
    except (ImportError, RuntimeError):
        # cannot done in parallel, then do in serial
        single_progress(func, arg_list, label, state)
    else:
        import sys
        # if the program is connect to terminal
        if sys.stdout.isatty():
            # initialize variable for progressbar
            bd_defaults = dict(type=Bar, kwargs=dict(max_value=bar_length))
            # get the pretty label
            label_dict = pretty_label(label, arg_list)
            general_label = label_dict[label]
            test_d = {general_label: {}}
            leaf_values = {}

            # special case for download
            if func == FETCH_CMD:
                for arg in arg_list:
                    url = state['index'][arg + '.tar.bz2'].get('url')
                    leaf_values[url] = Value(0)
                    test_d[general_label][label_dict[arg]] = \
                        BarDescriptor(value=leaf_values[url], **bd_defaults)
                    update_bar[url] = Value(0)
            else:
                for arg in arg_list:
                    leaf_values[arg] = Value(0)
                    test_d[general_label][label_dict[arg]] = \
                        BarDescriptor(value=leaf_values[arg], **bd_defaults)
                    update_bar[arg] = Value(0)
            # get the terminal
            t = Terminal()
            # Initialize a ProgressTree instance
            n = ProgressTree(term=t)
            # We'll use the make_room method to make sure the terminal
            #   is filled out with all the room we need
            n.make_room(test_d)
            # start the download thread
            from threading import Thread
            th = Thread(target=parallel_func, args=(state, arg_list, executor, func))
            th.start()
            # update the progress bar
            while not all(leaf_values[val].value == bar_length for val in leaf_values):
                n.cursor.restore()
                # update the progress bar by updating the leaf_values dictionary
                for val in leaf_values:
                    leaf_values[val].value = update_bar[val].value
                n.draw(test_d, BarDescriptor(bd_defaults))
            # wait until job finishes
            th.join()
        else:
            parallel_func(state, arg_list, executor, func)
