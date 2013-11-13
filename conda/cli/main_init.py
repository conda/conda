# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys
from os.path import isdir, join

import conda.config as config


descr = ("Initialize conda into a regular environment (when conda was "
         "installed as a Python package, e.g. using pip).")


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'init',
        description = descr,
        help = descr,
    )
    # TODO: add --force ?
    p.set_defaults(func=execute)


def is_initialized():
    return isdir(join(config.root_dir, 'conda-meta'))


def write_meta(meta_dir, info):
    import json

    with open(join(meta_dir, '%(name)s-%(version)s-0.json' % info), 'w') as fo:
        json.dump(info, fo, indent=2, sort_keys=True)


def execute(args, parser):
    import os

    if is_initialized():
        sys.exit('Error: conda appears to be already initalized in: %s' %
                 config.root_dir)

    prefix = config.root_dir
    print('Initializing conda into: %s' % prefix)

    meta_dir = join(prefix, 'conda-meta')
    try:
        os.mkdir(meta_dir)
    except OSError:
        sys.exit('Error: could not create: %s' % meta_dir)

    write_meta(meta_dir, dict(name='python', version=sys.version[:5]))
