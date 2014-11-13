from __future__ import absolute_import, print_function
import errno
import sys
from os.path import join

from conda import config, install
# TODO Move this to its new home once its found
from conda.cli.activate import binpath_from_arg


NO_WRITE_ACCESS = 80


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('..checkenv')
    p.add_argument(
        'environment'
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    binpath = binpath_from_arg(args.environment)
    # Make sure an env always has the conda symlink
    try:
        install.symlink_conda(join(binpath, '..'), config.root_dir)
    except (IOError, OSError) as e:
        if e.errno == errno.EPERM or e.errno == errno.EACCES:
            sys.exit(NO_WRITE_ACCESS)
        raise
    sys.exit(0)
