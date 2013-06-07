# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import common
import conda.config as config

descr = """
Modify configuration values in .condarc.  This is modeled after the git
config command.
"""

example = """
examples:
    conda config -add channels foo
"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'config',
        description = descr,
        help = descr,
        epilog = example,
        )
    common.add_parser_yes(p)
    p.set_defaults(func=execute)

def execute(args, parser):
    try:
        import yaml
    except ImportError:
        raise RuntimeError("pyyaml is required to modify configuration")
