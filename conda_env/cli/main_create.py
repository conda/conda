from __future__ import print_function

from argparse import RawDescriptionHelpFormatter
import os
import sys
import textwrap

from conda.cli import common, install as cli_install
from conda.gateways.disk.delete import rm_rf
from conda.misc import touch_nonadmin
from conda.plan import is_root_prefix

from .common import get_prefix
from .. import exceptions, specs
from ..installers.base import InvalidInstaller, get_installer

description = """
Create an environment based on an environment file
"""

example = """
examples:
    conda env create
    conda env create -n name
    conda env create vader/deathstar
    conda env create -f=/path/to/environment.yml
    conda env create -f=/path/to/requirements.txt -n deathstar
    conda env create -f=/path/to/requirements.txt -p /home/user/software/deathstar
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )
    p.add_argument(
        '-f', '--file',
        action='store',
        help='environment definition file (default: environment.yml)',
        default='environment.yml',
    )

    # Add name and prefix args
    common.add_parser_prefix(p)

    p.add_argument(
        '-q', '--quiet',
        action='store_true',
        default=False,
    )
    p.add_argument(
        'remote_definition',
        help='remote environment definition / IPython notebook',
        action='store',
        default=None,
        nargs='?'
    )
    p.add_argument(
        '--force',
        help=('force creation of environment (removing a previously existing '
              'environment of the same name).'),
        action='store_true',
        default=False,
    )
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    name = args.remote_definition or args.name

    try:
        spec = specs.detect(name=name, filename=args.file,
                            directory=os.getcwd())
        env = spec.environment

        # FIXME conda code currently requires args to have a name or prefix
        # don't overwrite name if it's given. gh-254
        if args.prefix is None and args.name is None:
            args.name = env.name

    except exceptions.SpecNotFound:
        raise

    prefix = get_prefix(args, search=False)

    if args.force and not is_root_prefix(prefix) and os.path.exists(prefix):
        rm_rf(prefix)
    cli_install.check_prefix(prefix, json=args.json)

    # TODO, add capability
    # common.ensure_override_channels_requires_channel(args)
    # channel_urls = args.channel or ()

    # special case for empty environment
    if not env.dependencies:
        from conda.install import symlink_conda
        from conda.base.context import context
        symlink_conda(prefix, context.root_dir)

    for installer_type, pkg_specs in env.dependencies.items():
        try:
            installer = get_installer(installer_type)
            installer.install(prefix, pkg_specs, args, env)
        except InvalidInstaller:
            sys.stderr.write(textwrap.dedent("""
                Unable to install package for {0}.

                Please double check and ensure you dependencies file has
                the correct spelling.  You might also try installing the
                conda-env-{0} package to see if provides the required
                installer.
                """).lstrip().format(installer_type)
            )
            return -1

    touch_nonadmin(prefix)
    if not args.json:
        print(cli_install.print_activate(args.name if args.name else prefix))
