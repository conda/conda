from os.path import join

from conda.config import root_dir



help_dir = join(root_dir, '.conda-help')


def ro_install(info=None):
    try:
        with open(join(help_dir, 'ro_install.txt')) as fi:
            msg = fi.read().decode('utf-8')
    except IOError:
        msg = """\
Error: Missing write permissions in: %(root_dir)s
#
# You don't appear to have the necessary permissions to install packages
# into the install area '%(root_dir)s'.
# However you can clone this environment into your home directory and
# then make changes to it.
# This may be done using the command:
#
# $ conda create -n my_%(name)s --clone=%(prefix)s %(args)s
"""
    if '%' in msg and info:
        return msg % info
    else:
        return msg
