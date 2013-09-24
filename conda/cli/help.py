import sys
from os.path import join

from conda.config import root_dir
from conda.cli.common import name_prefix


help_dir = join(root_dir, '.conda-help')


def root_read_only(command, prefix):
    assert command in {'install', 'update', 'remove'}
    try:
        with open(join(help_dir, 'ro_%s.txt' % command)) as fi:
            tmpl = fi.read().decode('utf-8')
    except IOError:
        tmpl = """\
Error: Missing write permissions in: %(root_dir)s
#
# You don't appear to have the necessary permissions to %(command)s packages
# into the install area '%(root_dir)s'.
# However you can clone this environment into your home directory and
# then make changes to it.
# This may be done using the command:
#
# $ conda create -n my_%(name)s --clone=%(prefix)s
"""

    if '%' in tmpl:
        msg = tmpl % dict(root_dir=root_dir,
                          prefix=prefix,
                          name=name_prefix(prefix),
                          command=command)
    else:
        msg = tmpl
    sys.exit(msg)
