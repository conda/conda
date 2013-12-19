import sys
import subprocess
from distutils.spawn import find_executable
import shlex

def call_args(string):
    args = shlex.split(string)
    arg0 = args[0]
    args[0] = find_executable(arg0)
    if not args[0]:
        sys.exit("Command not found: '%s'" % arg0)

    try:
        subprocess.check_call(args)
    except subprocess.CalledProcessError:
        sys.exit('Error: command failed: %s' % ' '.join(args))

# --- end header
