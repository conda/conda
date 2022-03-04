# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import codecs
from itertools import chain
import os
import sys

from ._vendor.six import (PY2, PY3, integer_types, iteritems, iterkeys, itervalues, string_types,
                          text_type, wraps)

PY2, PY3, integer_types, iteritems, iterkeys, itervalues, string_types = PY2, PY3, integer_types, iteritems, iterkeys, itervalues, string_types  # NOQA
text_type, wraps = text_type, wraps
from shlex import split
from tempfile import NamedTemporaryFile, template

try:
    from collections import OrderedDict as odict  # NOQA
except ImportError:
    from ordereddict import OrderedDict as odict  # NOQA


NoneType = type(None)
primitive_types = tuple(chain(string_types, integer_types, (float, complex, bool, NoneType)))


def isiterable(obj):
    # and not a string
    if PY2:
        return (hasattr(obj, '__iter__')
                and not isinstance(obj, string_types)
                and type(obj) is not type)
    else:
        try:
            from collections.abc import Iterable
        except ImportError:
            from collections import Iterable
        return not isinstance(obj, string_types) and isinstance(obj, Iterable)


# shlex.split() is a poor function to use for anything general purpose (like calling subprocess).
# It does not handle Unicode at all on Python 2 and it mishandles it on Python 3, but all is not
# lost. We can escape it, then escape the escapes then call shlex.split() then un-escape that.
def shlex_split_unicode(to_split, posix=True):
    # shlex.split does its own un-escaping that we must counter.
    if sys.version_info.major == 2:
        e_to_split = to_split.encode('unicode-escape').replace(b'\\', b'\\\\')
    else:
        e_to_split = to_split.replace('\\', '\\\\')
    splits = split(e_to_split, posix=posix)
    if sys.version_info.major == 2:
        return [bytes(s).decode('unicode-escape') for s in splits]
    else:
        return splits


def utf8_writer(fp):
    if sys.version_info[0] < 3:
        return codecs.getwriter('utf-8')(fp)
    else:
        return fp


if sys.version_info[0] < 3:
    def Utf8NamedTemporaryFile(mode='w+b', bufsize=-1, suffix="",
                               prefix=template, dir=None, delete=True):
        if 'CONDA_TEST_SAVE_TEMPS' in os.environ:
            delete = False
        return codecs.getwriter("utf-8")(
            NamedTemporaryFile(
                mode=mode,
                bufsize=bufsize,
                suffix=suffix,
                prefix=template,
                dir=dir,
                delete=delete,
            )
        )
else:
    def Utf8NamedTemporaryFile(mode='w+b', buffering=-1, newline=None,
                               suffix=None, prefix=None, dir=None, delete=True):
        if 'CONDA_TEST_SAVE_TEMPS' in os.environ:
            delete = False
        encoding = None
        if "b" not in mode:
            encoding = "utf-8"
        return NamedTemporaryFile(
            mode=mode,
            buffering=buffering,
            encoding=encoding,
            newline=newline,
            suffix=suffix,
            prefix=prefix,
            dir=dir,
            delete=delete,
        )


"""
def shlex_split_unicode(to_split, posix=True):
    if isinstance(to_split, string_types):
        t=string_types[0]
    elif isinstance(to_split, binary_type):
        t=binary_type
    to_split = ensure_text_type(to_split)
    e_to_split = to_split.encode('ascii', 'backslashreplace').replace(b'\\', b'\\\\')
    try:
        e_to_split = str(e_to_split, 'ascii')
    except:
        pass
    splits = split(e_to_split, posix=posix)
    if t == binary_type:
        res = [s.encode('unicode-escape') for s in splits]
    else:
        if sys.version_info[0] == 2:
            res = [s.decode('unicode-escape') for s in splits]
        else:
            res = [bytes(s, 'ascii').decode('unicode-escape') for s in splits]
    for r in res:
        assert isinstance(r, t)
    return res
from contextlib import contextmanager
import sys
#import shlex
#t = u'/var/folders/y1/ljv50nrs49gdqkrp01wy3_qm0000gn/T/190e_çñôáêß/bin/python3.5 -Wi -m compileall -q -l -i /var/folders/y1/ljv50nrs49gdqkrp01wy3_qm0000gn/T/tmp6tn_c5 ōγђ家固한áêñßôç'  # noqa: E501
#t2 = shlex.split(t)
class ImportBlocker(object):
    def __init__(self, args):
        self.module_names = [unicode(a) for a in args]
    def find_module(self, fullname, path=None):
        if unicode(fullname) in self.module_names:
            return self
        return None
    def find_spec(self, fullname, path, target=None):
        if fullname in self.module_names:
            return self
        return None
    def load_module(self, name):
        raise ImportError("%s is blocked and cannot be imported" % name)
@contextmanager
def blocked_imports(sys_module, *modules):
    old_modules = dict({})
    for m in modules:
        if m in sys_module.modules:
            old_modules[m] = sys_module.modules[m]
            del sys_module.modules[m]
    sys_meta_path = sys_module.meta_path[:]
    sys_module.meta_path.insert(0, ImportBlocker(modules))
    try:
        yield True
    finally:
        for k, v in old_modules.items():
            sys_module.modules[k] = v
        sys_module.meta_path = sys_meta_path
with blocked_imports('cStringIO'):
    if 'cStringIO' in sys.modules: print(sys.modules['cStringIO'])
    import shlex
    if 'cStringIO' in sys.modules: print(sys.modules['cStringIO'])
if 'cStringIO' in sys.modules: print(sys.modules['cStringIO'])
t = u'/var/folders/y1/ljv50nrs49gdqkrp01wy3_qm0000gn/T/190e_çñôáêß/bin/python3.5 -Wi -m compileall -q -l -i /var/folders/y1/ljv50nrs49gdqkrp01wy3_qm0000gn/T/tmp6tn_c5 ōγђ 家固한áêñßôç'  # noqa: E501
t2 = shlex.split(t)
"""
