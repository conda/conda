# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import re
import sys
import time

from os.path import exists, join, abspath, expanduser
from shutil import rmtree
from subprocess import check_call

isWin = sys.platform in ['win32', 'win64']

if isWin:
    status = True
else:
    status = False

def get_vers(pkg):
    output = open("tmp.txt", "w+")
    searchCommand = "conda search %s" % pkg
    check_call(searchCommand.split(), stdout = output, shell=status)
    output.close()

    infile = open("tmp.txt", "r")
    search_pat = re.compile(r"package: (%s-\d\.\d).*" % pkg)
    vers = search_pat.findall(infile.read())
    infile.close()

    vers = [version.replace('-', "=") for version in vers]

    if isWin:
        command = "del"
    else:
        command = "rm"
        
    removeCommand = "%s tmp.txt" % command
    check_call(removeCommand.split(), shell=status)

    return set(vers)


def get_conda_location():
    if isWin:
        return "C:\Anaconda\Scripts\conda.bat"
    else:
        return "conda"

def get_ipython_location():
    if isWin:
        return "C:\Anaconda\Scripts\ipython"
    else:
        return "ipython"

def get_tester_location(testdir):
    if isWin:
        return join(testdir, "Scripts", "anaconda-test.bat")
    else:
        return join(testdir, "bin", "anaconda-test")

def tester(py, num, testdir):
    logname = "%s-%s-testlog.txt" % (py, num)
    logfile = open(logname, "w+")
    tester = get_tester_location(testdir)
    print "\nRunning Anaconda package tests in %s for %s and %s.  This should take a while."  % (testdir, py, num)
    ret = check_call(tester.split(), stdout = logfile, stderr = logfile, shell=status)
    the_time = time.ctime()
    logfile.write(the_time)
    logfile.close()
    print "\nWriting log to %s" % logname



def gui_tester(pyVer,numVer, testdir):
    ipyloc = get_ipython_location()
    pylabCommand = "%s --pylab -ic 'plot(randn(99))'" % ipyloc
    check_call(pylabCommand.split(), shell=status)
    # qtconsole only works with python 2.7
    notebookCommand = "%s notebook" % ipyloc
    try:
        check_call(notebookCommand.split(), shell=status)
    except KeyboardInterrupt:
        pass
    if pyVer == "python=2.7":
        qtCommand = "%s qtconsole" % ipyloc
        check_call(qtCommand.split(), shell=status)
        check_call(join(testdir, "bin", "spyder"), shell=status)

def setup(gui = False):

    pys = get_vers("python")

    nums = get_vers("numpy")

    testdir = abspath(expanduser(join("~", "anaconda", "envs", "test")))

    for py in pys:
        for num in nums:

            if exists(testdir):
                rmtree(testdir)

            print "\n%s create -n test %s %s anaconda\n"  % (get_conda_location(), py, num)
            print "-"*60
            print
            createcmd = "%s create --yes -n test %s %s anaconda" % (get_conda_location(), py, num)
            check_call(createcmd.split(), shell=status)

            if gui == True:
                gui_tester(py, num, testdir)

            installcmd = "%s install --yes -n test test" % get_conda_location()
            print "\n", installcmd
            check_call(installcmd.split(), shell=status)

            tester(py,num,testdir)

            rmtree(testdir)