from __future__ import print_function, division, absolute_import

import logging
import sys
import hashlib
import collections
from functools import partial
from os.path import abspath, isdir, join
import os
import re


log = logging.getLogger(__name__)
stderrlog = logging.getLogger('stderrlog')

def can_open(file):
    """
    Return True if the given ``file`` can be opened for writing
    """
    try:
        fp = open(file, "ab")
        fp.close()
        return True
    except IOError:
        stderrlog.info("Unable to open %s\n" % file)
        return False


def can_open_all(files):
    """
    Return True if all of the provided ``files`` can be opened
    """
    for f in files:
        if not can_open(f):
            return False
    return True


def can_open_all_files_in_prefix(prefix, files):
    """
    Returns True if all ``files`` at a given ``prefix`` can be opened
    """
    return can_open_all((os.path.join(prefix, f) for f in files))

def try_write(dir_path):
    assert isdir(dir_path)
    # try to create a file to see if `dir_path` is writable, see #2151
    temp_filename = join(dir_path, '.conda-try-write-%d' % os.getpid())
    try:
        with open(temp_filename, mode='wb') as fo:
            fo.write(b'This is a test file.\n')
        os.unlink(temp_filename)
        return True
    except (IOError, OSError):
        return False


def hashsum_file(path, mode='md5'):
    h = hashlib.new(mode)
    with open(path, 'rb') as fi:
        while True:
            chunk = fi.read(262144)  # process chunks of 256KB
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def md5_file(path):
    return hashsum_file(path, 'md5')


def url_path(path):
    path = abspath(path)
    if sys.platform == 'win32':
        path = '/' + path.replace(':', '|').replace('\\', '/')
    return 'file://%s' % path


def win_path_to_unix(path, root_prefix=""):
    """Convert a path or ;-separated string of paths into a unix representation

    Does not add cygdrive.  If you need that, set root_prefix to "/cygdrive"
    """
    path_re = '(?<![:/^a-zA-Z])([a-zA-Z]:[\/\\\\]+(?:[^:*?"<>|]+[\/\\\\]+)*[^:*?"<>|;\/\\\\]+?(?![a-zA-Z]:))'  # noqa

    def translation(found_path):
        found = found_path.group(1).replace("\\", "/").replace(":", "")
        return root_prefix + "/" + found
    return re.sub(path_re, translation, path).replace(";/", ":/")


def unix_path_to_win(path, root_prefix=""):
    """Convert a path or :-separated string of paths into a Windows representation

    Does not add cygdrive.  If you need that, set root_prefix to "/cygdrive"
    """
    if len(path) > 1 and (";" in path or (path[1] == ":" and path.count(":") == 1)):
        # already a windows path
        return path.replace("/", "\\")

    path_re = root_prefix + '(/[a-zA-Z]\/(?:[^:*?"<>|]+\/)*[^:*?"<>|;]*)'

    def _translation(found_path):
        group = found_path.group(0)
        return group[len(root_prefix) + 1] + ":" + group[len(root_prefix) + 2:].replace("/", "\\")
    translation = re.sub(path_re, _translation, path)
    translation = re.sub(":?([a-zA-Z]):\\\\",
                         lambda match: ";" + match.group(0)[1] + ":\\",
                         translation)
    return translation


# curry cygwin functions
def win_path_to_cygwin(path):
    return win_path_to_unix(path, "/cygdrive")

def cygwin_path_to_win(path):
    return unix_path_to_win(path, "/cygdrive")


def translate_stream(stream, translator):
    return "\n".join(translator(line) for line in stream.split("\n"))


def human_bytes(n):
    """
    Return the number of bytes n in more human readable form.
    """
    if n < 1024:
        return '%d B' % n
    k = n/1024
    if k < 1024:
        return '%d KB' % round(k)
    m = k/1024
    if m < 1024:
        return '%.1f MB' % m
    g = m/1024
    return '%.2f GB' % g


class memoized(object):
    """Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args, **kw):
        newargs = []
        for arg in args:
            if isinstance(arg, list):
                newargs.append(tuple(arg))
            elif not isinstance(arg, collections.Hashable):
                # uncacheable. a list, for instance.
                # better to not cache than blow up.
                return self.func(*args, **kw)
            else:
                newargs.append(arg)
        newargs = tuple(newargs)
        key = (newargs, frozenset(kw.items()))
        if key in self.cache:
            return self.cache[key]
        else:
            value = self.func(*args, **kw)
            self.cache[key] = value
            return value


# For instance methods only
class memoize(object):  # 577452
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)

    def __call__(self, *args, **kw):
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(kw.items()))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res


def find_parent_shell(path=False):
    """return process name or path of parent.  Default is to return only name of process."""
    try:
        import psutil
    except ImportError:
        sys.exit("No psutil available.\n"
                 "To proceed, please conda install psutil")
    process = psutil.Process()
    while "conda" in process.parent().name():
        process = process.parent()
    if path:
        return process.parent().exe()
    return process.parent().name()


@memoized
def get_yaml():
    try:
        import raml as yaml
    except ImportError:
        try:
            import yaml
        except ImportError:
            sys.exit("No yaml library available.\n"
                     "To proceed, please conda install raml")
    return yaml


def yaml_load(filehandle):
    yaml = get_yaml()
    try:
        return yaml.load(filehandle, Loader=yaml.RoundTripLoader, version="1.2")
    except AttributeError:
        return yaml.load(filehandle)


def yaml_dump(string):
    yaml = get_yaml()
    try:
        return yaml.dump(string, Dumper=yaml.RoundTripDumper,
                         block_seq_indent=2, default_flow_style=False,
                         indent=4)
    except AttributeError:
        return yaml.dump(string, default_flow_style=False)
