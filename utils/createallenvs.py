import os

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


def envTest(pyver, numver):
    os.system("rm -rf ~/anaconda/envs/test")
    print "\nconda create -n test %s %s anaconda\n --------------\n" % (pyver, numver)
    os.system("conda create --confirm=no -n test %s %s anaconda" % (pyver, numver))
    os.system("conda install --confirm=no -n test test")
    os.system("./../anaconda/envs/test/bin/anaconda-test | tee -a %s-%s-testlog.txt" % (pyver, numver))


for py in pys:
    for num in nums:
        envTest(py, num)
        
rmtree(test)