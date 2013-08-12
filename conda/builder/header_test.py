import sys
from distutils.spawn import find_executable
from subprocess import check_call


if sys.platform == 'win32':
    bin_dir = sys.prefix + r'\Scripts'
else:
    bin_dir = sys.prefix + '/bin'

def cmd_args(string):
    args = string.split()
    arg0 = args[0]
    args[0] = find_executable(arg0, path=bin_dir)
    if not args[0]:
        sys.exit("Command not found: '%s'" % arg0)
    return args

# --- end header
