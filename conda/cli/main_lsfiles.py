# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
import re

from conda.cli import common
import conda.config as config

descr = "List all files belonging to specified package."

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'lsfiles',
        description = descr,
        help = descr,
    )
    p.add_argument(
        'pkg_regex',
        action = "store",
        nargs = "+",
    )
    p.set_defaults(func=execute)

def listDirContent(dirPath):

    for root, dirs, files in os.walk(dirPath):
        for fileName in files:
            filePath = root+"/"+fileName
            print(filePath)
    print("")

def listPackagesFiles(pkg_regex=None):
    pkgsDir = config.pkgs_dirs[0]
    allDirNames = []
    numOfPkgRegex = len(pkg_regex)
    totalWidth = len(str(numOfPkgRegex))
    totalNum = 0

    for item in os.listdir(pkgsDir):
        if not os.path.isfile(pkgsDir+"/"+item):
            allDirNames.append(item)

    print('\nBase location for packages: %s\n' % (pkgsDir))

    for pkgRegex in pkg_regex:
        totalNum += 1
        allMatchDirNames = []
        pattern = re.compile(pkgRegex, re.I)

        for dirName in allDirNames:
            search = pattern.search(dirName)

            if search:
                allMatchDirNames.append(dirName)

        numOfMatchDirNames = len(allMatchDirNames)

        if numOfMatchDirNames == 0:
            print("Regular expression %s doesn't match any package, omitting." % (pkgRegex))
            print("")
            continue

        dirNumWidth = len(str(numOfMatchDirNames))
        num = 0

        for matchDirName in allMatchDirNames:
            num += 1
            pkgDir = pkgsDir+'/'+matchDirName

            print("{totalnum:>{totalWidth}} : [ {num:>{width}} / {total} ] Content of '{regex}' pkg_regex (this match: {dir}):".format(
                    totalnum=totalNum, totalWidth=totalWidth, num=num, width=dirNumWidth, total=numOfMatchDirNames, regex=pkgRegex, dir=pkgDir))
            listDirContent(pkgDir)

def execute(args, parser):

    listPackagesFiles(args.pkg_regex)
