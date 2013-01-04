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


def get_conda_location():
    if sys.platform in ['win32', 'win64']:
        return "C:\Anaconda\Scripts\conda.bat"
    else:
        return "conda"

def get_ipython_location():
    if sys.platform in ['win32', 'win64']:
        return "C:\Anaconda\Scripts\ipython"
    else:
        return "ipython"

def get_tester_location(testdir):
    if sys.platform in ['win32', 'win64']:
        return join(testdir, "Scripts", "anaconda-test")
    else:
        return join(testdir, "bin", "anaconda-test")

def execute(gui = False):

    pys = [
        "python=2.7"
    ]

    nums = [
        "numpy=1.6",
    ]

    if sys.platform not in ['win32', 'win64']:
        pys.append("python=2.6")
        nums.append("numpy=1.5")
        nums.append("numpy=1.7")

    testdir = abspath(expanduser(join("~", "anaconda", "envs", "test")))

    for py in pys:
        for num in nums:
            if exists(testdir):
                rmtree(testdir)
            print "\n%s create -n test %s %s anaconda\n"  % (get_conda_location(), py, num)
            print "-"*60
            print
            createcmd = "%s create --yes -n test %s %s anaconda" % (get_conda_location(), py, num)
            check_call(createcmd.split())
            if gui == True:
                ipyloc = get_ipython_location()
                pylabCommand = "%s --pylab -ic 'plot(randn(99))'" % ipyloc
                check_call(pylabCommand.split())
                # qtconsole only works with python 2.7
                notebookCommand = "%s notebook" % ipyloc
                # This line uses os.system because check_call will always exit on ctrl+c, and ipython notebook requires
                # the user to press ctrl+c to continue the script.  With check_call, this exits everything.
                os.system(notebookCommand)
                if py == "python=2.7":
                    qtCommand = "%s qtconsole" % ipyloc
                    check_call(qtCommand.split())
                    check_call(join(testdir, "bin", "spyder"))
            installcmd = "%s install --yes -n test test" % get_conda_location()
            print "\n", installcmd
            check_call(installcmd.split())
            logname = "%s-%s-testlog.txt" % (py, num)
            logfile = open(logname, "w+")
            tester = get_tester_location(testdir)
            print "\nRunning Anaconda package tests in %s for %s and %s.  This may take a while."  % (testdir, py, num)
            ret = check_call(tester.split(), stdout = logfile, stderr = logfile)
            print
            print "*~"*40
            if ret == 0:
                print " "*20, "PASSED!"
            else:
                print " "*20, "FAILED!"
            print "*~"*40
            print
            rmtree(testdir)