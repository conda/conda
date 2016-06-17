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

progress_cmds = set([RM_EXTRACTED, LINK, UNLINK])
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

    to_download = []

    for instruction, arg in plan:

        log.debug(' %s(%r)' % (instruction, arg))
        cmd = _commands.get(instruction)

        if cmd is None:
            raise InvalidInstruction(instruction)

        if state['i'] is not None and instruction in progress_cmds:
            state['i'] += 1
            getLogger('progress.update').info((name_dist(arg), state['i'] - 1))

        # if it is fetch command
        # put that command in a list for future multi-thread processing
        if cmd == FETCH_CMD:
            to_download.append((state, arg))
            continue

        # if it is a extract command
        # start the fetch multi-thread process
        # and put extract into a list
        if cmd == EXTRACT_CMD:
            if to_download:
                packages_multithread_cmd(FETCH_CMD, to_download)
                to_download = None
                # to_extract.append((state, arg))
                # continue

        # if it is a link command
        # start the extract multi-thread process
        """
        if cmd == PRINT_CMD:
            if to_extract:
                packages_multithread_cmd(EXTRACT_CMD, to_extract)
                to_extract = None
        """
        cmd(state, arg)

        if state['i'] is not None and instruction in progress_cmds and state['maxval'] == state['i']:
            state['i'] = None
            getLogger('progress.stop').info(None)

    messages(state['prefix'])


class DownloadBar:
    """
        A class for download progress bar using click progress bar
    """

    def __init__(self, length, label):
        self.length = length
        self.label = label
        self.t = threading.Thread(target=self.consumer, args=(self.length, self.label))

    def __enter__(self):
        self.t.daemon = True
        self.t.start()

    def __exit__(self, *args):
        self.t.join(timeout=0.01)
        self.t.is_alive()

    @staticmethod
    def consumer(length, label):
        with click.progressbar(length=length, label=label) as bar:
            while True:
                if not q.empty():
                    size = q.get(True)
                    bar.update(size)

    def producer(self, size):
        q.put(size)
