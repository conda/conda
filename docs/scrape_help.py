#!/usr/bin/env python
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from subprocess import Popen, STDOUT, PIPE
from os.path import join
import re
import sys

cmd_names = [
    'info',
    'help',
    'list',
    'search',
    'create',
    'install',
    'update',
    'remove',
    'config',
    'init',
    'clean',
    'build',
    'skeleton',
    'package',
    'bundle',
    'index',
]

def scrape_help(cmd_name):

    cmd = "CIO_TARGET='ce' COLUMNS=1000 conda %s -h" % cmd_name

    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)

    output = p.stdout.read().decode('utf-8')


    if cmd_name in ['remove','package','install', 'config']:

        # groups:
        usage_pat = re.compile(r'(usage): (conda .*\n\s*.*\n\s*.*)')

        # groups:                           -----1----
        desc_pat = re.compile(r'usage.*\n\s*(.*\n\s*.*)')
    else:
        # groups:                ----1---- -----2----
        usage_pat = re.compile(r'(usage): (conda .*)\n')

        # groups:                          --1-
        desc_pat = re.compile(r'usage.*\n\n(.*)\n\n')


    usage = usage_pat.search(output)
    desc = desc_pat.search(output)




    # groups:                                               --1--   --2-
    positional_pat = re.compile(r'positional arguments:\n\s+(\w*)\s+(.*)\n')
    pos = positional_pat.search(output)

    # groups:                            ---1--
    optional_pat = re.compile(r'(optional(.*\n)*)$')
    opt = optional_pat.search(output)

    if opt:
        options = opt.group(1)

        yn_pat = re.compile(r'{.*}')
        options = yn_pat.sub('', options)

        rd_pat = re.compile(r'(default: )(.*/anaconda)')
        options = rd_pat.sub(r"\1ROOT_DIR", options)

        in_pat = re.compile(r'(in )(.*/anaconda)')
        options = in_pat.sub(r"\1ROOT_DIR", options)

    else:
        options = ''

    output = desc.group(1)

    output += "\n\n**%s**: ``%s``\n\n" % (usage.group(1), usage.group(2))

    if pos:
        output += "*%s*\n\t%s\n\n" % (pos.group(1), pos.group(2))

    output += options

    return output



if __name__ == '__main__':

    for name in cmd_names:
        path = "source/commands/"
        if len(sys.argv) > 1:
            path = sys.argv[1]
        outpath = join(path, "%s.txt" % name)

        print("Scraping help for '%s' -> %s" % (name, outpath))

        output = scrape_help(name)


        outfile = open(outpath, "w")
        outfile.write(output)
        outfile.close()
