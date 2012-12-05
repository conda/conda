import sys
import platform
from os.path import normpath



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


if __name__ == '__main__':
    print PLATFORM
    print ARCH_NAME
