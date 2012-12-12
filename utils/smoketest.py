import os

from subprocess import call
from os.path import exists, join
from shutil import rmtree
from tempfile import mkdtemp

base = mkdtemp()

myenv = join(base, "myenv")

TESTLOG="conda-testlog.txt"

if exists(TESTLOG):
    os.remove(TESTLOG)

f = open(TESTLOG, "w")

cmds = [
    "conda info",
    "conda list ^m.*lib$",
    "conda search ^m.*lib$",
    "conda depends numpy",
    "conda envs",
    "conda create --confirm=no -p %s sqlite" % myenv,
    "conda install --confirm=no -p %s pandas=0.8.1" % myenv,
    "conda update --confirm=no -p %s pandas" % myenv,
    "conda activate --confirm=no -p %s numba-0.3.1-np17py27_0" % myenv,
    "conda deactivate --confirm=no -p %s sqlite-3.7.13-0" % myenv,
    "conda remove --confirm=no zeromq-2.2.0-0",
    "conda download --confirm=no zeromq-2.2.0-0"
]

fails = []

for i in cmds:
    cmd = i
    print "-"*61
    print "%s" % cmd 
    print "-"*61 
    try:
        ret = call(cmd.split())
        if ret != 0:
            print "\nFAILED\n"
            f.write("\n%s" % cmd)
            fails.append(cmd)
        else:
            print "\nPASSED\n"
    except Exception as e:
        print e
        f.write("\nThe script had the following error running %s: %s" % (cmd, e))

if fails:
    print "These commands failed: \n"
    for line, fail in enumerate(fails, 1):
        print "%d: %s\n" % (line, fail)
    print "Writing failed commands to conda-testlog.txt"

try:
    rmtree(myenv)
except:
    pass