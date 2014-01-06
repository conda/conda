from __future__ import print_function, division, absolute_import

import sys
from os.path import islink, isfile


# extensions which are assumed to belong to non-ELF files
NO_EXT = (
    '.py', '.pyc', '.pyo', '.h', '.a', '.c', '.txt', '.html',
    '.xml', '.png', '.jpg', '.gif',
    '.o' # ELF but not what we are looking for
)

MAGIC = b'\x7fELF'


def is_elf(path):
    if path.endswith(NO_EXT) or islink(path) or not isfile(path):
        return False
    with open(path, 'rb') as fi:
        head = fi.read(4)
    return bool(head ==  MAGIC)


if __name__ == '__main__':
    if sys.platform.startswith('linux'):
        for path in '/usr/bin/ls', '/etc/mtab':
            print(path, is_elf(path))
