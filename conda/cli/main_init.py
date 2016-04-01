# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys
from os.path import isdir, join

import conda
import conda.config as config

descr = """
Initialize conda into a regular environment (when conda was installed as a
Python package, e.g. using pip). (DEPRECATED)
"""

warning = """
WARNING: conda init is deprecated. The recommended way to manage pip installed
conda is to use pip to manage the root environment and conda to manage new
conda environments.

Note that pip installing conda is not the recommended way for setting up your
system.  The recommended way for setting up a conda system is by installing
Miniconda. See http://conda.pydata.org/miniconda.html."""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'init',
        description=descr,
        epilog=warning,
        help=descr,
    )
    p.set_defaults(func=execute)


def is_initialized():
    return isdir(join(config.root_dir, 'conda-meta'))


def write_meta(meta_dir, info):
    import json

    info['files'] = []
    with open(join(meta_dir,
                   '%(name)s-%(version)s-0.json' % info), 'w') as fo:
        json.dump(info, fo, indent=2, sort_keys=True)


def initialize(prefix=config.root_dir):
    import os

    meta_dir = join(prefix, 'conda-meta')
    try:
        os.mkdir(meta_dir)
    except OSError:
        sys.exit('Error: could not create: %s' % meta_dir)
    with open(join(meta_dir, 'foreign'), 'w') as fo:
        fo.write('python\n')
        if sys.platform != 'win32':
            fo.write('zlib sqlite readline tk openssl system\n')
    write_meta(meta_dir, dict(name='conda',
                              version=conda.__version__.split('-')[0],
                              build_number=0))
    write_meta(meta_dir, dict(name='python',
                              version=sys.version[:5],
                              build_number=0,
                              build="0"))
    with open(join(meta_dir, "pinned"), 'w') as f:
        f.write("python %s 0" % sys.version[:5])


def execute(args, parser):
    if is_initialized():
        sys.exit('Error: conda appears to be already initalized in: %s' %
                 config.root_dir)

    print(warning, file=sys.stderr)

    print('Initializing conda into: %s' % config.root_dir)
    initialize()
