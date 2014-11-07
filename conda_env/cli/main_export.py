from argparse import RawDescriptionHelpFormatter
from copy import copy
import os
import sys
import textwrap

import yaml

from conda.cli import common
from conda.cli import main_list
from conda import config
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

    p.add_argument(
        '-n', '--name',
        action='store',
        help='name of environment (in %s)' % os.pathsep.join(config.envs_dirs),
        default=None,
    )

    p.add_argument(
        '-f', '--file',
        default=None,
        required=False
    )

    p.set_defaults(func=execute)


def execute(args, parser):
    if not args.name:
        # Note, this is a hack fofr get_prefix that assumes argparse results
        # TODO Refactor common.get_prefix
        name = os.environ.get('CONDA_DEFAULT_ENV', False)
        if not name:
            msg = "Unable to determine environment\n\n"
            msg += textwrap.dedent("""
                Please re-run this command with one of the following options:

                * Provide an environment name via --name or -n
                * Re-run this command inside an activated conda environment.""").lstrip()
            # TODO Add json support
            common.error_and_exit(msg, json=False)
        args.name = name
    prefix = common.get_prefix(args)

    installed = install.linked(prefix)
    conda_pkgs = copy(installed)
    # json=True hides the output, data is added to installed
    main_list.add_pip_installed(prefix, installed, json=True)

    pip_pkgs = sorted(installed - conda_pkgs)

    dependencies = ['='.join(a.rsplit('-', 2)) for a in sorted(conda_pkgs)]
    if len(pip_pkgs) > 0:
        dependencies.append({'pip': ['=='.join(a.rsplit('-', 2)[:2]) for a in pip_pkgs]})

    data = {
        'name': args.name,
        'dependencies': dependencies,
    }
    if args.file is None:
        fp = sys.stdout
    else:
        fp = open(args.file, 'wb')
    yaml.dump(data, default_flow_style=False, stream=fp)
