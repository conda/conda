import os
import sys

import conda_argparse
from conda.config import root_dir
from conda.cli.common import confirm_yn, add_parser_yes

try:
    WindowsError
except NameError:
    class WindowsError(Exception): pass

def main(args, windowsonly=True):
    if sys.platform == 'win32' or not windowsonly:
        if args.yes:
            check_processes()
        else:
            while not check_processes():
                confirm_yn(args, default='no')

def check_processes():
    # Conda should still work if psutil is not installed (it should not be a
    # hard dependency)
    try:
        import psutil
        # Old versions of psutil don't have this error, causing the below code to
        # fail.
        psutil._error.AccessDenied
    except ImportError:
        return True

    ok = True
    curpid = os.getpid()
    for n in psutil.get_pid_list():
        if n == curpid:
            # The Python that conda is running is OK
            continue
        try:
            p = psutil.Process(n)
        except psutil._error.NoSuchProcess:
            continue
        try:
            if os.path.realpath(p.exe).startswith(os.path.realpath(root_dir)):
                processcmd = ' '.join(p.cmdline)
                print "WARNING: the process %s (%d) is running" % (processcmd, n)
                ok = False
        except (psutil._error.AccessDenied, WindowsError):
            pass
    if not ok:
        print("WARNING: Continuing installation while the above processes are "
            "running is not recommended.\n"
            "Close all Anaconda programs before installing or updating things with conda.")
    return ok

if __name__ == '__main__':
    p = conda_argparse.ArgumentParser()
    add_parser_yes(p)
    args = p.parse_args()
    main(args, windowsonly=False)
