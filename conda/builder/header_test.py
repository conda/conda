import os
import sys
import subprocess
from distutils.spawn import find_executable


if sys.platform == 'win32':
    bin_dir = sys.prefix + r'\Scripts'
else:
    bin_dir = sys.prefix + '/bin'


def call_args(string):
    args = string.split()
    arg0 = args[0]
    args[0] = find_executable(arg0, path=os.environ['PATH'])
    if not args[0]:
        sys.exit("Command not found: '%s'" % arg0)

    try:
        subprocess.check_call(args)
    except subprocess.CalledProcessError:
        sys.exit('Error: command failed: %s' % ' '.join(args))

# --- end header
