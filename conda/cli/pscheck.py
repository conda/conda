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
            if os.path.relpath(p.exe).startswith(os.path.realpath(root_dir)):
                print "Warning: the process %s is running" % p.name
                conflicts = True
        except psutil._error.AccessDenied:
            pass
    return conflicts

if __name__ == '__main__':
    main()
