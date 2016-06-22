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

progress_cmds = set([FETCH])

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


def FETCH_CMD(state, arg, bar=None):
    fetch_pkg(state['index'][arg + '.tar.bz2'], bar=bar)


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

fetch_q = Queue(500)

action_message = {
    FETCH_CMD: "[ Downloading Packages   ",
    EXTRACT_CMD: "[ Extracting Packages    ",
    RM_EXTRACTED_CMD: "[ RM Extracting Packages ",
    LINK_CMD: "[ Linking Packages       ",
    UNLINK_CMD: "[ Unlinking Packages     "
}


def fetch_callback(fn):
    if fn:
        log.debug(fn.result())
    fetch_q.put(None, False)


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
        with click.progressbar(package_list, label=action_message[cmd]) as bar:
            for arg_download in bar:
                cmd(state, arg_download)
    else:
        """
            Declare size and label for progress bar
            Downloading are different than other command.
        """
        size = 0
        for arg in package_list:
            inc = state['index'][arg + '.tar.bz2']['size'] \
                if "size" in state['index'][arg + '.tar.bz2'] else 0
            size += inc

        label = action_message[cmd] + " ]" if cmd in action_message else str(cmd)
        # start progress bar
        futures = []
        with ProgressBar(size, label, len(package_list)) as bar:
            try:
                for arg_d in package_list:
                    future = executor.submit(cmd, state, arg_d, fetch_q)
                    future.add_done_callback(fetch_callback)
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
        # start = time.time()
        packages_multithread_cmd(cmd, state, arg)
        # print("Time for downloading", time.time() -start)
    messages(state['prefix'])



class ProgressBar:
    """
        A class for download progress bar using click progress bar
        Mainly using click progress bar
        Use blocking queue to update the progress bar
        length : length of progress bar, for download, it is the size of all packages to be downloaded
        label : The label of download bar
        num : number of packages to be downloaded
    """
    def __init__(self, length, label, num):
        self.length = length
        self.label = label
        self.t = threading.Thread(target=self.consumer, args=())
        self.lock = threading.Lock()
        self.num = num

    def __enter__(self):
        self.t.daemon = True
        self.t.start()
        return self

    def __exit__(self, *args):
        while self.t.is_alive():
            self.t.join(timeout=0.001)

    """
        using producer and consumer mode
        Each download thread produces to the queue,
        and the printing thread get from the queue
        Finish when get enough None object
    """
    def consumer(self):
        with click.progressbar(length=self.length, label=self.label) as bar:
            while self.num != 0:
                if not fetch_q.empty():
                    size = fetch_q.get(True)
                    if size:
                        bar.update(size)
                    else:
                        self.num -= 1
