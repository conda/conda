import os
import subprocess as sp
import sys
import time

from os.path import exists, join
from shutil import rmtree
from tempfile import mkdtemp

base = mkdtemp()
myenv = join(base, "env")

# CIO_TEST needs to be set to 2 if any of the packages tested below are only found in the test repo.

# os.environ['CIO_TEST'] = 2

cmds = [
    "conda info",
    "conda list ^m.*lib$",
    "conda search ^m.*lib$",
    "conda search -v numpy",    
    "conda search -c numpy",
    "conda info -e",
    "conda creae --yes -p %s sqlite python=2.6" % myenv,
    "conda install --yes -p %s pandas=0.8.1" % myenv,
    "conda install --yes -p %s numba=0.1.1" % myenv,
    "conda install --yes -p %s cython=0.16" % myenv,
    "conda install --yes -p %s cython=0.17.3" % myenv,
    "conda install --yes -p %s accelerate" % myenv,
    "conda remove --yes -p %s accelerate" % myenv,
    "conda update --yes -p %s pandas" % myenv,
    "conda install --yes -p %s iopro" % myenv,
    "conda remove --yes -p %s iopro" % myenv,
    "conda info -e",
    "conda info -a",
    "conda info --license",
    "conda info -s",
]

def tester(commands):
    cmds = commands
    errs = []
    fails = []
    for cmd in cmds:
        print "-"*120
        print "%s" % cmd
        print "-"*120
        try:
            child = sp.Popen(cmd.split(), stdout=sp.PIPE, stderr=sp.PIPE)
            data, err = child.communicate()
            ret = child.returncode
            if ret != 0:
                print "\nFAILED\n"
                errs.append("\n%s\n \n%s" % (cmd, err))
                fails.append(cmd)
            else:
                print "\nPASSED\n"
        except Exception as e:
            print e
            f.write("\nThe script had the following error running %s: %s" % (cmd, e))

    return (fails, errs)


if __name__ == '__main__':
    TESTLOG = ''
    if len(sys.argv) == 2 and sys.argv[1] == 'log':
        TESTLOG="conda-testlog.txt"
    fails, errs = tester(cmds)
    if fails:
        print "These commands failed: \n"
        for line, fail in enumerate(fails, 1):
            print "%d: %s\n" % (line, fail)
        print "Writing failed commands to conda-testlog.txt"
        header = 'Test Results For %s' % time.asctime()
        if TESTLOG:
            with open(TESTLOG, "a") as f:
                f.write('%s\n%s\n' % (header, '-'*len(header)))
                for error in errs:
                    f.write(error)

    try:
        rmtree(myenv)
    except:
        pass
