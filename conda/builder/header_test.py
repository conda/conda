
import sys
from distutils.spawn import find_executable
from subprocess import check_call

if sys.platform == 'win32':
    bin_dir = sys.prefix + r'\Scripts'
else:
    bin_dir = sys.prefix + '/bin'

def cmd_args(string):
    args = string.split()
    args[0] = find_executable(args[0], path=bin_dir)
    return args

# --- end header
