# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

"""
Tools for converting conda packages

"""
from __future__ import print_function, division
import re

libpy_pat = re.compile(
    r'(lib/python\d\.\d|Lib)'
    r'/(site-packages|lib-dynload)/(\S+?)(\.cpython-\d\dm)?\.(so|pyd)')
def show_cext(t):
    for m in t.getmembers():
        match = libpy_pat.match(m.path)
        if match is None:
            continue
        x = match.group(3)
        print('import', x.replace('/', '.'))

def has_cext(t):
    for m in t.getmembers():
        if libpy_pat.match(m.path):
            return True
    return False
