import os

import psutil

from conda.config import root_dir

def main():
    ok = True
    for n in psutil.get_pid_list():
        try:
            p = psutil.Process(n)
        except psutil._error.NoSuchProcess:
            continue
        try:
            if os.path.realpath(p.exe).startswith(os.path.realpath(root_dir)):
                print "WARNING: the process %s (%d) is running" % (p.name, n)
                ok = False
        except psutil._error.AccessDenied:
            pass
    if not ok:
        print("WARNING: Continuing installation while the above processes are "
            "running is not recommended.")
    return ok

if __name__ == '__main__':
    main()
