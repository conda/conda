# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys
from os.path import isdir, join

import conda.config as config


descr = "Initialize conda in a regular Python environment."


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'init',
        description = descr,
        help = descr,
    )
    # TODO: add --force
    p.set_defaults(func=execute)


def is_initialized():
    return isdir(join(config.root_dir, 'conda-meta'))


def execute(args, parser):
    if is_initialized():
        sys.exit('Error: conda appears to be already initalized in: %s' %
                 config.root_dir)

    print('Initializing conda into: %s' % config.root_dir)
    # TODO...
    raise NotImplemented
