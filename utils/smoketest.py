import os
import subprocess as sp

from os.path import exists, join
from shutil import rmtree
from tempfile import mkdtemp

base = mkdtemp()
myenv = join(base, "env")

# CIO_TEST needs to be set to 2 if any of the packages tested below are only found in the test repo.

# os.environ['CIO_TEST'] = 2

cmds = [
    (
        "conda info"
    ),
    (
        "conda list ^m.*lib$"
    ),
    (
        "conda search ^m.*lib$"
    ),
    (
        "conda search --all -v numpy"
    ),
    (
        "conda depends numpy"
    ),
    (
        "conda info -e"
    ),
    (
        "conda create --yes -p %s sqlite python=2.6" % myenv
    ),
    (
        "conda install --yes -p %s pandas=0.8.1" % myenv
    ),
    (
        "conda install --yes -p %s numba=0.1.1" % myenv
    ),
    (
        "conda install --yes -p %s cython=0.16" % myenv
    ),
    (
        "conda install --yes -p %s cython=0.17.3" % myenv
    ),
    (
        "conda install --yes -p %s accelerate" % myenv
    ),
    (
        "conda remove --yes -p %s accelerate" % myenv
    ),
    (
        "conda update --yes -p %s pandas" % myenv
    ),
    (
        "conda install --yes -p %s iopro" % myenv
    ),
    (
        "conda remove --yes -p %s iopro" % myenv
    ),
    (
        "conda local --yes -d numba-0.3.1-np17py27_0"
    ),
    (
        "conda env --yes -lp %s numba-0.3.1-np17py27_0" % myenv
    ),
    (
        "conda env --yes -up %s sqlite-3.7.13-0" % myenv
    ),
    (
        "conda local --yes -r zeromq-2.2.0-0"
    ),
    (
        "conda local --yes -d zeromq-2.2.0-0"
    )
]

def tester(commands):
    cmds = commands
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
                f.write("\n%s\n \n%s" % (cmd, err))
                fails.append(cmd)
            else:
                print "\nPASSED\n"
        except Exception as e:
            print e
            f.write("\nThe script had the following error running %s: %s" % (cmd, e))

    return fails


if __name__ == '__main__':
    TESTLOG="conda-testlog.txt"
    if exists(TESTLOG):
        os.remove(TESTLOG)
    f = open(TESTLOG, "w")
    fails = tester(cmds)
    f.close()
    if fails:
        print "These commands failed: \n"
        for line, fail in enumerate(fails, 1):
            print "%d: %s\n" % (line, fail)
        print "Writing failed commands to conda-testlog.txt"

    try:
        rmtree(myenv)
    except:
        pass
