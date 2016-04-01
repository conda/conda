import os
import subprocess as sp
import sys
import time

from os.path import exists, join
from shutil import rmtree
from tempfile import mkdtemp

base = mkdtemp()
myenv = join(base, "env")

if 'win' in sys.platform and 'dar' not in sys.platform:
    status = True
    pandas = numba = '0.10.1'
    cython = '0.18'
else:
    status = False
    pandas = '0.8.1'
    numba = '0.1.1'
    cython = '0.16'


# CIO_TEST needs to be set to 2 if any of the packages tested below are
# only found in the test repo.

# os.environ['CIO_TEST'] = 2

cmds = [
    "info",
    "list ^m.*lib$",
    "search ^m.*lib$",
    "search -v numpy",
    "search -c numpy",
    "info -e",
    "create --yes -p %s sqlite python=2.6" % myenv,
    "install --yes -p %s pandas=%s" % (myenv, pandas),
    "remove --yes -p %s pandas" % myenv,
    "install --yes -p %s numba=%s" % (myenv, numba),
    "install --yes -p %s cython=%s" % (myenv, cython),
    "remove --yes -p %s cython" % myenv,
    "install --yes -p %s accelerate" % myenv,
    "remove --yes -p %s accelerate" % myenv,
    "install --yes -p %s mkl" % myenv,
    "remove --yes -p %s mkl" % myenv,
    "update --yes -p %s numba" % myenv,
    "remove --yes -p %s numba" % myenv,
    "install --yes -p %s iopro" % myenv,
    "remove --yes -p %s iopro" % myenv,
    "info -e",
    "info -a",
    "info --license",
    "info -s",
]

def tester(commands):
    cmds = commands
    errs = []
    fails = []
    for cmd in cmds:
        cmd = "conda %s" % cmd
        print("-"*len(cmd))
        print("%s" % cmd)
        print("-"*len(cmd))
        try:
            child = sp.Popen(cmd.split(), stdout=sp.PIPE, stderr=sp.PIPE, shell=status)
            data, err = child.communicate()
            ret = child.returncode
            if ret != 0:
                print("\nFAILED\n")
                errs.append("\n%s\n \n%s" % (cmd, err))
                fails.append(cmd)
            else:
                print("\nPASSED\n")
        except Exception as e:
            print(e)
            errs.append("\nThe script had the following error running %s: %s" % (cmd, e))

    return (fails, errs)


if __name__ == '__main__':

    TESTLOG = 'conda-testlog.txt'

    options = True if len(sys.argv) > 1 else False

    if options and 'new' in sys.argv:
        if exists(TESTLOG):
            os.remove(TESTLOG)

    fails, errs = tester(cmds)
    if fails:
        print("These commands failed: \n")
        for line, fail in enumerate(fails, 1):
            print("%d: %s\n" % (line, fail))
        header = 'Test Results For %s' % time.asctime()
        if options and 'log' in sys.argv:
            print("Writing failed commands to conda-testlog.txt")
            with open(TESTLOG, "a") as f:
                f.write('%s\n%s\n' % (header, '-'*len(header)))
                for error in errs:
                    f.write(error)

    try:
        rmtree(myenv)
    except:
        pass
