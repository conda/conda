import os

import psutil

from conda.config import root_dir

def main():
    conflicts = False
    for n in psutil.get_pid_list():
        try:
            p = psutil.Process(n)
        except psutil._error.NoSuchProcess:
            continue
        try:
            if os.path.realpath(p.exe).startswith(os.path.realpath(root_dir)):
                print "WARNING: the process %s (%d) is running" % (p.name, n)
                conflicts = True
        except psutil._error.AccessDenied:
            pass
    if conflicts:
        print("WARNING: Continuing installation while the above processes are "
            "running is not recommended.")
    return conflicts

if __name__ == '__main__':
    main()
