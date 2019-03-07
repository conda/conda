# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import collections
from itertools import chain

from ._vendor.five import WhateverIO as StringIO, with_metaclass
from ._vendor.six import (PY2, PY3, integer_types, iteritems, iterkeys, itervalues, string_types,
                          text_type, wraps)
StringIO, with_metaclass = StringIO, with_metaclass
PY2, PY3, integer_types, iteritems, iterkeys, itervalues, string_types = PY2, PY3, integer_types, iteritems, iterkeys, itervalues, string_types  # NOQA
text_type, wraps = text_type, wraps
from shlex import split

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
        return not isinstance(obj, string_types) and isinstance(obj, collections.Iterable)


# shlex.split() is a poor function to use for anything general purpose (like calling subprocess).
# It does not handle Unicode at all on Python 2 and it mishandles it on Python 3, but all is not
# lost. We can escape it, then escape the escapes then call shlex.split() then un-escape that.
def shlex_split_unicode(to_split, posix=True):
    # shlex.split does its own un-escaping that we must counter.
    e_to_split = to_split.replace('\\', '\\\\').encode('unicode-escape')
    splits = split(e_to_split, posix=posix)
    return [bytes(s).decode('unicode-escape') for s in splits]


'''
from contextlib import contextmanager
import sys

#import shlex
#t = u'/var/folders/y1/ljv50nrs49gdqkrp01wy3_qm0000gn/T/190e_çñôáêß/bin/python3.5 -Wi -m compileall -q -l -i /var/folders/y1/ljv50nrs49gdqkrp01wy3_qm0000gn/T/tmp6tn_c5 ōγђ家固한áêñßôç'
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

t = u'/var/folders/y1/ljv50nrs49gdqkrp01wy3_qm0000gn/T/190e_çñôáêß/bin/python3.5 -Wi -m compileall -q -l -i /var/folders/y1/ljv50nrs49gdqkrp01wy3_qm0000gn/T/tmp6tn_c5 ōγђ 家固한áêñßôç'
t2 = shlex.split(t)
'''
