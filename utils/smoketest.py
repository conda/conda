import os

 
from os.path import exists
from shutil import rmtree
from tempfile import mkdtemp

myenv = mkdtemp()

TESTLOG="conda-testlog.txt"

# Check if TESTLOG exists, removes it

if exists(TESTLOG):
    os.remove(TESTLOG)

cmds = [
    "conda info",
    "conda list ^m.*lib$",
    "conda search ^m.*lib$",
    "conda depends numpy",
    "conda envs",
    "conda create --confirm=no -n myenv sqlite",
    "conda install --confirm=no -n myenv pandas=0.8.1",
    "conda update --confirm=no -n myenv pandas",
    "conda activate --confirm=no -p ~/anaconda/envs/myenv numba-0.3.1-np17py27_0",
    "conda deactivate --confirm=no -n myenv sqlite-3.7.13-0",
    "conda remove --confirm=no zeromq-2.2.0-0",
    "conda download --confirm=no zeromq-2.2.0-0"
]

for cmd in cmds:
    print "-"*61
    print "%s" % cmd 
    print "-"*61 
    os.system(cmd)

rmtree(myenv)