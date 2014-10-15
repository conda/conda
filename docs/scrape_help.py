#!/usr/bin/env python
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from subprocess import check_output
from os.path import join, dirname, abspath, isdir
from os import makedirs, chdir
import sys

def conda_help(cache=[]):
    if cache:
        return cache[0]
    cache.append(check_output(['conda', '--help']))
    return cache[0]

def conda_commands():
    help = conda_help()
    commands = []
    start = False
    for line in help.splitlines():
        # Commands start after "command" header
        if line.strip() == 'command':
            start = True
            continue
        if start:
            # The end of the commands
            if not line:
                break
            if line[4] != ' ':
                commands.append(line.split()[0])
    return commands

def external_commands():
    help = conda_help()
    commands = []
    start = False
    for line in help.splitlines():
        # Commands start after "command" header
        if line.strip() == 'external commands:':
            start = True
            continue
        if start:
            # The end of the commands
            if not line:
                break
            if line[4] != ' ':
                commands.append(line.split()[0])
    return commands

def generate_man(command):
    chdir(abspath(dirname(__file__)))
    manpath = join('build', 'man')
    if not isdir(manpath):
        makedirs(manpath)
    conda_version = check_output(['conda', '--version'])
    print("Generating manpage for conda %s" % command)
    check_output([
        'help2man',
        '--name', 'conda %s' % command,
        '--section', '1',
        '--source', 'Continuum Analytics',
        '--version-string', conda_version,
        '--no-info',
        'conda %s' % command,
        '-o', join(manpath, 'conda-%s.1' % command)
        ])

def generate_html(command):
    # Make sure to replace hard-coded paths
    pass


def main():
    commands = sys.argv[1:] or conda_commands()

    for command in commands:
        generate_man(command)


if __name__ == '__main__':
    sys.exit(main())
