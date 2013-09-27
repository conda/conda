import sys
from os.path import join

import conda.config as config
from conda.cli.common import name_prefix


help_dir = join(config.root_dir, '.conda-help')


def root_read_only(command, prefix):
    assert command in {'install', 'update', 'remove'}
    for path in [join(help_dir, 'ro_%s.txt' % command),
                 join(help_dir, 'ro.txt')]:
        try:
            with open(path) as fi:
                tmpl = fi.read().decode('utf-8')
            break
        except IOError:
            pass
    else:
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
        msg = tmpl % dict(root_dir=config.root_dir,
                          prefix=prefix,
                          name=name_prefix(prefix),
                          env0=config.envs_dirs[0],
                          command=command)
    else:
        msg = tmpl
    sys.exit(msg)
