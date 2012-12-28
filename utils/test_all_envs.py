import os
import sys

from os.path import exists, join, abspath, expanduser
from shutil import rmtree

pys = [
    "python=2.6",
    "python=2.7"
]

nums = [
    "numpy=1.5",
    "numpy=1.6",
    "numpy=1.7"
]


def envTest(pyver, numver, gui=False):
    if not exists("test-tmp"):
        os.system("mkdir-test-tmp")
    if gui == True:
        os.system("ipython --pylab -ic 'plot(randn(99))'")
        os.system("ipython qtconsole")
        os.system("ipython notebook")
        os.system("spyder")
    testdir = abspath(expanduser(join("~", "anaconda", "envs", "test")))
    if exists(testdir):
        rmtree(testdir)
    print "\nconda create -n test %s %s anaconda\n"  % (pyver, numver)
    print "-"*60
    print
    os.system("conda create --yes -n test %s %s anaconda" % (pyver, numver))
    os.system("conda install --yes -n test test")
    logname = "%s-%s-testlog.txt" % (pyver, numver)
    testcmd = "%s 2>&1 >> %s" % (join(testdir, "bin", "anaconda-test"), join("test-tmp", logname))
    os.system(testcmd)


if __name__ == '__main__':
    for py in pys:
        for num in nums:
            if len(sys.argv) == 2:
                if sys.argv[1] in ["-g", "--gui"]:
                    envTest(py, num, gui=True)
            else:
                envTest(py, num)
    