from __future__ import absolute_import, division, print_function

from logging import getLogger

from .config import root_dir
from .exceptions import InvalidInstruction
from .fetch import fetch_pkg
from .install import (is_extracted, messages, extract, rm_extracted, rm_fetched, LINK_HARD,
                      link, unlink, symlink_conda, package_cache)
from .utils import find_parent_shell
import threading
import click
import sys

if float(sys.version.split()[0][:3]) < 2.8:
    from Queue import Queue
else:
    from queue import Queue

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

progress_cmds = set([FETCH, RM_EXTRACTED])

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
    # getLogger('print').info(arg)
    pass


def FETCH_CMD(state, arg, bar=None):
    fetch_pkg(state['index'][arg + '.tar.bz2'], bar=bar)


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
    symlink_conda(state['prefix'], arg, find_parent_shell(path=False))

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

fetch_q = Queue(500)
extract_q = Queue(500)
rm_extracted_q = Queue(500)
link_q = Queue(500)
unlink_q = Queue(500)

action_queue = {
    FETCH_CMD: fetch_q,
    EXTRACT_CMD: extract_q,
    RM_EXTRACTED_CMD: rm_extracted_q,
    LINK_CMD: link_q,
    UNLINK_CMD: unlink_q
}
action_message = {
    FETCH_CMD: "[ Downloading Packages   ",
    EXTRACT_CMD: "[ Extracting Packages    ",
    RM_EXTRACTED_CMD: "[ RM Extracting Packages ",
    LINK_CMD: "[ Linking Packages       ",
    UNLINK_CMD: "[ Unlinking Packages     "
}


def extract_callback(fn):
    if fn:
        log.debug(fn.result())
    extract_q.put(1, False)


def rm_extract_callback(fn):
    if fn:
        log.debug(fn.result())
    rm_extracted_q.put(1, False)


def link_callback(fn):
    if fn:
        log.debug(fn.result())
    link_q.put(1, False)


def unlink_callback(fn):
    if fn:
        log.debug(fn.result())
    unlink_q.put(1, False)


def default_callback(fn):
    if fn:
        log.debug(fn.result())


def fetch_callback(fn):
    if fn:
        log.debug(fn.result())
    fetch_q.put(1, False)


action_callback = {
    FETCH_CMD: fetch_callback,
    EXTRACT_CMD: extract_callback,
    RM_EXTRACTED_CMD: rm_extract_callback,
    LINK_CMD: link_callback,
    UNLINK_CMD: unlink_callback
}


def packages_multithread_cmd(cmd, state, package_list):
    """
    Try to execute the command the packages in multi-thread
    :param cmd, the command need to execute
    :param state, contains the index of each action
    :param package_list: the list of packages and metadata for download
    :return: nothing
    """
    """
     Try to importsour the concurrent futures library
     If successes, use multi-thread pool to download
     Otherwise, download in series
    """
    try:
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(5)
    except (ImportError, RuntimeError):
        # concurrent.futures is only available in Python >= 3.2 or if futures is installed
        # RuntimeError is thrown if number of threads are limited by OS
        for arg_download in package_list:
            cmd(state, arg_download)
        return None
    else:

        """
            Declare size and label for progress bar
            Downloading are different than other command.
        """
        size = len(package_list)
        label = action_message[cmd] + " ]" if cmd in action_message else str(cmd)
        # start progress bar
        futures = []
        with ProgressBar(size, label, cmd):
            try:
                for arg_d in package_list:
                    future = executor.submit(cmd, state, arg_d)
                    future.add_done_callback(action_callback[cmd] if
                                             cmd in action_callback else default_callback)
                    futures.append(future)
            finally:
                executor.shutdown(wait=True)
                log.debug((f.result() for f in futures))
                # Check for download result
                if cmd == FETCH_CMD:
                    for arg_d in package_list:
                        assert arg_d in package_cache()


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
        if instruction not in progress_cmds:
            if cmd == PREFIX_CMD:
                cmd(state, arg[0])
            else:
                label = action_message[cmd] + " ]" if \
                    cmd in action_message else str(cmd)
                with click.progressbar(arg, label=label) as bar:
                    for ar in bar:
                        cmd(state, ar)

            continue
        # Done in parallel
        packages_multithread_cmd(cmd, state, arg)
    messages(state['prefix'])


class ProgressBar:
    """
        A class for download progress bar using click progress bar
    """
    def __init__(self, length, label, cmd):
        self.length = length
        self.label = label
        self.t = threading.Thread(target=self.consumer, args=())
        self.s = 0
        self.lock = threading.Lock()
        self.cmd = cmd

    def __enter__(self):
        self.t.daemon = True
        self.t.start()
        return self

    def __exit__(self, *args):
        self.t.join(timeout=0.01)
        if self.t.is_alive():
            assert False

    def consumer(self):
        with click.progressbar(length=self.length, label=self.label) as bar:
            while self.s < self.length:
                if self.cmd not in action_queue:
                    break
                if not action_queue[self.cmd].empty():
                    size = action_queue[self.cmd].get(True)
                    bar.update(size)
                    self.s += size
