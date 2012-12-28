# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import signal
import sys
import time

from os.path import exists, join, abspath, expanduser
from utils import add_parser_prefix, get_prefix
from shutil import rmtree
from subprocess import check_call

def execute(gui = False):

    pys = [
        "python=2.6",
        "python=2.7"
    ]

    nums = [
        "numpy=1.5",
        "numpy=1.6",
        "numpy=1.7"
    ]

    if not exists("test-tmp"):
        check_call("mkdir test-tmp".split())
    testdir = abspath(expanduser(join("~", "anaconda", "envs", "test")))

    for py in pys:
        for num in nums:
            if exists(testdir):
                rmtree(testdir)
            if gui == True:
                check_call("ipython --pylab -ic 'plot(randn(99))'".split())
                check_call("ipython qtconsole".split())
                # This line uses os.system because check_call will always exit on ctrl+c, and ipython notebook requires
                # the user to press ctrl+c to continue the script.  With check_call, this exits everything.
                os.system("ipython notebook")
                check_call("spyder")
            print "\nconda create -n test %s %s anaconda\n"  % (py, num)
            print "-"*60
            print
            createcmd = "conda create --yes -n test %s %s anaconda" % (py, num)
            check_call(createcmd.split())
            # os.system("conda create --yes -n test %s %s anaconda" % (py, num))
            installcmd = "conda install --yes -n test test"
            check_call(installcmd.split())
            # os.system("conda install --yes -n test test")
            logname = "%s-%s-testlog.txt" % (py, num)
            testcmd = "%s 2>&1 >> %s" % (join(testdir, "bin", "anaconda-test"), join("test-tmp", logname))
            # os.system(testcmd)
            check_call(testcmd.split())