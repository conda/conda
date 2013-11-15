from __future__ import print_function, division, absolute_import

import subprocess
from os.path import islink, isfile


NO_EXT = (
    '.py', '.pyc', '.pyo', '.h', '.a', '.c', '.txt', '.html',
    '.xml', '.png', '.jpg', '.gif',
)

MAGIC = {
    '\xca\xfe\xba\xbe': 'MachO-universal',
    '\xce\xfa\xed\xfe': 'MachO-i386',
    '\xcf\xfa\xed\xfe': 'MachO-x86_64',
    '\xfe\xed\xfa\xce': 'MachO-ppc',
    '\xfe\xed\xfa\xcf': 'MachO-ppc64',
}


def is_macho(path):
    if path.endswith(NO_EXT) or islink(path) or not isfile(path):
        return False
    with open(path, 'rb') as fi:
        head = fi.read(4)
    return bool(head in MAGIC)


def otool(path):
    "thin wrapper around otool -L"
    lines = subprocess.check_output(['otool', '-L', path]).splitlines()
    assert lines[0].startswith(path), path
    res = []
    for line in lines[1:]:
        assert line[0] == '\t'
        res.append(line.split()[0])
    return res


def install_name_change(path, cb_func):
    """
    change dynamic shared library install names of Mach-O binary `path`.

    `cb_func` is a callback function which called for each shared library name.
    It is called with `path` and the current shared library install name,
    and return the new name (or None if the name should be unchanged).
    """
    changes = []
    for link in otool(path):
        new_link = cb_func(path, link)
        if new_link:
            changes.append((link, new_link))

    for old, new in changes:
        args = ['install_name_tool', '-change', old, new, path]
        print(' '.join(args))
        subprocess.check_call(args)
