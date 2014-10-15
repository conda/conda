#!/usr/bin/env python
# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from subprocess import check_output, PIPE, Popen
from os.path import join, dirname, abspath, isdir
from os import makedirs, chdir, pathsep
from collections import OrderedDict

import sys
import json

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

def man_replacements():
    # XXX: We should use conda-api for this, but it's currently annoying to set the
    # root prefix with.
    info = json.loads(check_output(['conda', 'info', '--json']))
    # We need to use an ordered dict because the root prefix should be
    # replaced last, since it is typically a substring of the default prefix
    r = OrderedDict([
        (info['default_prefix'], r'default prefix'),
        (pathsep.join(info['envs_dirs']), r'envs dirs'),
        # For whatever reason help2man won't italicize these on its own
        (info['rc_path'], r'\fI\,user .condarc path\/\fP'),
        # Note this requires at conda > 3.7.1
        (info['sys_rc_path'], r'\fI\,system .condarc path\/\fP'),
        (info['root_prefix'], r'root prefix'),
        ])
    return r

manpath = join(dirname(__file__), 'build', 'man')

def generate_man(command):
    if not isdir(manpath):
        makedirs(manpath)
    conda_version = check_output(['conda', '--version'])
    print("Generating manpage for conda %s" % command)
    manpage = check_output([
        'help2man',
        '--name', 'conda %s' % command,
        '--section', '1',
        '--source', 'Continuum Analytics',
        '--version-string', conda_version,
        '--no-info',
        'conda %s' % command,
        ])

    replacements = man_replacements()
    for text in replacements:
        manpage = manpage.replace(text, replacements[text])
    with open(join(manpath, 'conda-%s.1' % command), 'w') as f:
        f.write(manpage)

def generate_html(command):
    print("Generating html for conda %s" % command)
    # Use abspath so that it always has a path separator
    man = Popen(['man', abspath(join(manpath, 'conda-%s.1' % command))], stdout=PIPE)
    htmlpage = check_output(['man2html'], stdin=man.stdout)

    with open(join(manpath, 'conda-%s.html' % command), 'w') as f:
        f.write(htmlpage)


def main():
    commands = sys.argv[1:] or conda_commands()

    for command in commands:
        generate_man(command)
        generate_html(command)

if __name__ == '__main__':
    sys.exit(main())
