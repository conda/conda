from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import abspath

from conda.cli import conda_argparse
from conda.config import root_dir
from conda.cli.common import confirm, add_parser_yes

try:
    WindowsError
except NameError:
    class WindowsError(Exception):
        pass

def main(args, windowsonly=True):
    # Returns True for force, otherwise None
    if sys.platform == 'win32' or not windowsonly:
        if args.yes:
            check_processes()
        else:
            while not check_processes():
                choice = confirm(args, message="Continue (yes/no/force)",
                    choices=('yes', 'no', 'force'), default='no')
                if choice == 'no':
                    sys.exit(1)
                if choice == 'force':
                    return True

def check_processes():
    # Conda should still work if psutil is not installed (it should not be a
    # hard dependency)
    try:
        import psutil
        # Old versions of psutil don't have this error,
        # causing the below code to fail.
        psutil._error.AccessDenied
    except:
        return True

    ok = True
    curpid = os.getpid()
    for n in psutil.get_pid_list():
        if n == curpid: # The Python that conda is running is OK
            continue
        try:
            p = psutil.Process(n)
        except psutil._error.NoSuchProcess:
            continue
        try:
            if abspath(p.exe).startswith(root_dir):
                processcmd = ' '.join(p.cmdline)
                if processcmd.startswith('conda '):
                    continue
                print("WARNING: the process %s (%d) is running" %
                      (processcmd, n))
                ok = False
        except (psutil._error.AccessDenied, WindowsError):
            pass
    if not ok:
        print("""\
WARNING: Continuing installation while the above processes are running is
not recommended.  Please, close all Anaconda programs before installing or
updating things with conda.
""")
    return ok

if __name__ == '__main__':
    p = conda_argparse.ArgumentParser()
    add_parser_yes(p)
    args = p.parse_args()
    main(args, windowsonly=False)
