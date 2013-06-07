import os
import sys
import platform
from distutils.spawn import find_executable
from subprocess import check_call

system = {'linux2': 'linux', 'linux': 'linux',
          'darwin': 'osx', 'win32': 'win'}[sys.platform]
arch = int(os.getenv('ARCH', 64))
assert 8 * tuple.__itemsize__ == arch
if system == 'linux' and platform.machine() == 'armv6l':
    assert arch == 32
    plat = 'linux-armv6l'
else:
    plat = '%s-%s' % (system, arch)

cfg = dict(ANA_PY=int(os.getenv('ANA_PY', 27)),
           ANA_NPY=int(os.getenv('ANA_NPY', 17)),
           PRO=int(os.getenv('PRO', 0)),
           plat=plat)

if sys.platform == 'win32':
    bin_dir = sys.prefix + r'\Scripts'
else:
    bin_dir = sys.prefix + '/bin'

def cmd_args(string):
    args = string.split()
    args[0] = find_executable(args[0], path=bin_dir)
    return args

def applies(cond):
    return eval(cond, ns_cfg(cfg), {})

for kv in cfg.items():
    print('%s = %r' % kv)

# --- end header
