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


manpath = join(dirname(__file__), 'build', 'man')
if not isdir(manpath):
    makedirs(manpath)
rstpath = join(dirname(__file__), 'source', 'commands')
if not isdir(rstpath):
    makedirs(rstpath)

RST_HEADER = """
conda %s
=======================

.. raw:: html

"""

def str_check_output(*args, **kwargs):
    return check_output(*args, **kwargs).decode('utf-8')

def conda_help(cache=[]):
    if cache:
        return cache[0]
    cache.append(str_check_output(['conda', '--help']))
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
    info = json.loads(str_check_output(['conda', 'info', '--json']))
    # We need to use an ordered dict because the root prefix should be
    # replaced last, since it is typically a substring of the default prefix
    r = OrderedDict([
        (info['default_prefix'].encode('utf-8'), rb'default prefix'),
        (pathsep.join(info['envs_dirs']).encode('utf-8'), rb'envs dirs'),
        # For whatever reason help2man won't italicize these on its own
        (info['rc_path'].encode('utf-8'), rb'\fI\,user .condarc path\/\fP'),
        # Note this requires at conda > 3.7.1
        (info['sys_rc_path'].encode('utf-8'), rb'\fI\,system .condarc path\/\fP'),
        (info['root_prefix'].encode('utf-8'), rb'root prefix'),
        ])

    return r

def generate_man(command):
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
    with open(join(manpath, 'conda-%s.1' % command), 'wb') as f:
        f.write(manpage)

def generate_html(command):
    print("Generating html for conda %s" % command)
    # Use abspath so that it always has a path separator
    man = Popen(['man', abspath(join(manpath, 'conda-%s.1' % command))], stdout=PIPE)
    htmlpage = check_output([
        'man2html',
        '-bare', # Don't use HTML, HEAD, or BODY tags
        'title', 'conda-%s' % command,
        '-topm', '0', # No top margin
        '-botm', '0', # No bottom margin
        ],
        stdin=man.stdout)

    with open(join(manpath, 'conda-%s.html' % command), 'wb') as f:
        f.write(htmlpage)


def write_rst(command):
    print("Generating rst for conda %s" % command)
    with open(join(manpath, 'conda-%s.html' % command), 'r') as f:
        html = f.read()

    with open(join(rstpath, 'conda-%s.rst' % command), 'w') as f:
        f.write(RST_HEADER % command)
        for line in html.splitlines():
            f.write('   ')
            f.write(line)
            f.write('\n')

def main():
    commands = sys.argv[1:] or conda_commands()

    for command in commands:
        generate_man(command)
        generate_html(command)
        write_rst(command)

if __name__ == '__main__':
    sys.exit(main())
