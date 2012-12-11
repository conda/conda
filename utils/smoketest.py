import os

 
from os.path import exists, join
from shutil import rmtree
from tempfile import mkdtemp

base = mkdtemp()

myenv = join(base, "myenv")

TESTLOG="conda-testlog.txt"

if exists(TESTLOG):
    os.remove(TESTLOG)

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

for cmd in cmds:
    print "-"*61
    print "%s" % cmd 
    print "-"*61 
    os.system(cmd)

rmtree(myenv)