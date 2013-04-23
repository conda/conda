import sys
import hashlib
import platform
from os.path import normpath, getmtime, getsize



SYS_MAP = {'linux2': 'linux', 'darwin': 'osx', 'win32': 'win'}
PLATFORM = SYS_MAP.get(sys.platform, 'unknown')

BITS = int(platform.architecture()[0][:2])
ARCH_NAME = {64: 'x86_64', 32: 'x86'}[BITS]


def rel_lib(f):
    assert not f.startswith('/')
    if f.startswith('lib/'):
        return normpath((f.count('/') - 1) * '../')
    else:
        return normpath(f.count('/') * '../') + '/lib'


def md5_file(path):
    with open(path, 'rb') as fi:
        h = hashlib.new('md5')
        while True:
            chunk = fi.read(262144)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def file_info(path):
    return {'size': getsize(path),
            'md5': md5_file(path),
            'mtime': getmtime(path)}


if __name__ == '__main__':
    print PLATFORM
    print ARCH_NAME
