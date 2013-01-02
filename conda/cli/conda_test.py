# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import sys

from os.path import exists, join, abspath, expanduser
from shutil import rmtree
from subprocess import check_call

def execute(gui = False):

    pys = [
        # "python=2.6",
        "python=2.7"
    ]

    nums = [
        "numpy=1.5",
        "numpy=1.6",
        "numpy=1.7"
    ]

    testdir = abspath(expanduser(join("~", "anaconda", "envs", "test")))

    for py in pys:
        for num in nums:
            if exists(testdir):
                rmtree(testdir)
            print "\nconda create -n test %s %s anaconda\n"  % (py, num)
            print "-"*60
            print
            createcmd = "conda create --yes -n test %s %s anaconda" % (py, num)
            check_call(createcmd.split())
            if gui == True:
                ipyloc = join(testdir, "bin", "ipython")
                pylabCommand = "%s --pylab -ic 'plot(randn(99))'" % ipyloc
                check_call(pylabCommand.split())
                # qtCommand = "%s qtconsole" % ipyloc
                # check_call(qtCommand.split())
                notebookCommand = "%s notebook" % ipyloc
                # This line uses os.system because check_call will always exit on ctrl+c, and ipython notebook requires
                # the user to press ctrl+c to continue the script.  With check_call, this exits everything.
                os.system(notebookCommand)
                if py == "python=2.7":
                    check_call(join(testdir, "bin", "spyder"))
            installcmd = "conda install --yes -n test test"
            check_call(installcmd.split())
            logname = "%s-%s-testlog.txt" % (py, num)
            logfile = open(logname, "w+")
            tester = join(testdir, "bin", "anaconda-test")
            testcmd = tester
            ret = check_call(tester.split())
            print
            print "*~"*40
            if ret == 0:
                print " "*20, "PASSED!"
            else:
                print " "*20, "FAILED!"
            print "*~"*40
            print
            check_call(tester.split(), stdout = logfile)
            rmtree(testdir)