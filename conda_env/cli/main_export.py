from argparse import RawDescriptionHelpFormatter
from copy import copy
import sys

import yaml

from conda.cli import common
from conda.cli import main_list
from conda import install

description = """
Export a given environment
"""

example = """
examples:
    conda env export
    conda env export --file SOME_FILE
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'export',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )

    common.add_parser_prefix(p)

    p.add_argument(
        '-f', '--file',
        default=None,
        required=False
    )

    p.set_defaults(func=execute)


def execute(args, parser):
    prefix = common.get_prefix(args)

    installed = install.linked(prefix)
    conda_pkgs = copy(installed)
    # json=True hides the output, data is added to installed
    main_list.add_pip_installed(prefix, installed, json=True)

    pip_pkgs = sorted(installed - conda_pkgs)

    dependencies = ['='.join(a.rsplit('-', 2)) for a in sorted(conda_pkgs)]
    dependencies.append({'pip': ['=='.join(a.rsplit('-', 2)[:2]) for a in pip_pkgs]})

    data = {
        'dependencies': dependencies,
    }
    if args.file is None:
        fp = sys.stdout
    else:
        fp = open(args.file, 'wb')
    yaml.dump(data, default_flow_style=False, stream=fp)
