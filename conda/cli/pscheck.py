import os

import psutil

from conda.config import root_dir

def main():
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
        except psutil._error.AccessDenied:
            pass
    if not ok:
        print("WARNING: Continuing installation while the above processes are "
            "running is not recommended.\n"
            "Close all Anaconda programs before updating conda.")
    return ok

if __name__ == '__main__':
    main()
