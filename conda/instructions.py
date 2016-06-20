from __future__ import absolute_import, division, print_function

from logging import getLogger

from .config import root_dir
from .exceptions import InvalidInstruction
from .fetch import fetch_pkg
from .install import (is_extracted, messages, extract, rm_extracted, rm_fetched, LINK_HARD,
                      link, unlink, symlink_conda, name_dist, package_cache)
from .utils import find_parent_shell
import threading
import click
import sys

if float(sys.version.split()[0][:3]) < 2.8:
    from Queue import Queue
else:
    from queue import Queue

log = getLogger(__name__)
q = Queue(500)

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

def fetchCallback(fn):
    if fn:
        log.debug(fn.result())

def extractCallback(fn):
    if fn:
        log.debug(fn.result())
    extract_q.put(1)

def rmExtractCallback(fn):
    if fn:
        log.debug(fn.result())
    rm_extracted_q.put(1)

def linkCallback(fn):
    if fn:
        log.debug(fn.result())
    link_q.put(1)

def unlinkCallback(fn):
    if fn:
        log.debug(fn.result())
    unlink_q.put(1)

def defaultCallback(fn):
    if fn:
        log.debug(fn.result())


action_callback = {
    FETCH_CMD: fetchCallback,
    EXTRACT_CMD: extractCallback,
    RM_EXTRACTED_CMD: rmExtractCallback,
    LINK_CMD: linkCallback,
    UNLINK_CMD: unlinkCallback
}


def packages_multithread_cmd(cmd, state, package_list):
    """
    Try to download the packages in multi-thread
    :param download_list: the list of packages and metadata for  downloadinh
    :return: nothing
    """
    """
     Try to import the concurrent futures library
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
        if cmd == FETCH_CMD:
            size = 0
            if isinstance(package_list, list):
                for arg_d in package_list:
                    size += state['index'][str(arg_d) + '.tar.bz2']['size']
            else:
                size += state['index'][str(package_list) + '.tar.bz2']['size']
        else:
            size = len(package_list) if isinstance(package_list, list) else 1

        res = " ".join([ar for ar in package_list if "-" in ar]) if isinstance(package_list,
                                                                               list) else package_list.split()[0]
        label = action_message[cmd] + res + " ]" if cmd in action_message else str(cmd)
        with ProgressBar(size, label, cmd):
            try:
                if not isinstance(package_list, list):
                    package_list = [package_list]
                for arg_d in package_list:
                    if cmd == FETCH_CMD:
                        future = executor.submit(cmd, state, arg_d, action_queue[cmd])
                    else:
                        future = executor.submit(cmd, state, arg_d)
                    future.add_done_callback(action_callback[cmd] if cmd in action_callback else defaultCallback)

            finally:
                executor.shutdown(wait=True)
                # Check for download result
                if cmd == FETCH_CMD:
                    for arg_d in package_list:
                        assert arg_d in package_cache()


def packages_multithread_cmd(cmd, package_list):
    """
    Try to download the packages in multi-thread
    :param download_list: the list of packages and metadata for  downloadinh
    :return: nothing
    """
    """
     Try to import the concurrent futures library
     If successes, use multi-thread pool to download
     Otherwise, download in series
    """
    try:
        import concurrent.futures

        executor = concurrent.futures.ThreadPoolExecutor(5)
    except (ImportError, RuntimeError):
        # concurrent.futures is only available in Python >= 3.2 or if futures is installed
        # RuntimeError is thrown if number of threads are limited by OS
        for state_download, arg_download in package_list:
            cmd(state_download, arg_download)

        return None
    else:
        assert cmd == FETCH_CMD

        size = 0
        for state_d, arg_d in package_list:
            size += state_d['index'][arg_d + '.tar.bz2']['size']
        res = " ".join([ar for st, ar in package_list])
        label = "[ Downloading Packages " + res + " ]"
        with DownloadBar(size, label):
            try:
                futures = tuple(executor.submit(cmd, state_d, arg_d,
                                                q) for state_d, arg_d in package_list)
                log.debug((f.result() for f in futures))
            finally:
                executor.shutdown(wait=True)
                # Check for download result
                for state_d, arg_d in package_list:
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

    for instruction, arg in plan.iteritems():
        log.debug(' %s(%r)' % (instruction, arg))
        cmd = _commands.get(instruction)
        if cmd is None:
            raise InvalidInstruction(instruction)

        if instruction not in progress_cmds:
            if isinstance(arg, list):
                for ar in arg:
                    cmd(state, ar)
            else:
                cmd(state, arg)
            continue
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
        self.t.is_alive()

    def consumer(self):
        try:
            self.lock.acquire()
            with click.progressbar(length=self.length, label=self.label) as bar:
                while self.s < self.length:
                    if self.cmd not in action_queue:
                        break
                    if not action_queue[self.cmd].empty():
                        size = action_queue[self.cmd].get()

                        bar.update(size)
                        self.s += size
        finally:
            self.lock.release()

