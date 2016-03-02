from argparse import RawDescriptionHelpFormatter
import os
import textwrap
import sys

from conda import config
from conda.cli import common
from conda.cli import install as cli_install
from conda.misc import touch_nonadmin

from ..installers.base import get_installer, InvalidInstaller
from .. import specs as install_specs
from .. import exceptions

description = """
Update the current environment based on environment file
"""

example = """
examples:
    conda env update
    conda env update -n=foo
    conda env update -f=/path/to/environment.yml
    conda env update --name=foo --file=environment.yml
    conda env update vader/deathstar
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'update',
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
        action='store',
        help='environment definition (default: environment.yml)',
        default='environment.yml',
    )
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
        '--select',
        action='append',
        help="toggle preprocessing selectors. pass multiple times to toggle multiple selectors. pass 'all' to toggle all selectors",
        metavar="SELECTORS",
    )
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    name = args.remote_definition or args.name

    try:
        spec = install_specs.detect(name=name, filename=args.file,
                                    directory=os.getcwd(), selectors=args.select)
        env = spec.environment
    except exceptions.SpecNotFound as e:
        common.error_and_exit(str(e), json=args.json)

    if not args.name:
        if not env.name:
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

        # Note: stubbing out the args object as all of the
        # conda.cli.common code thinks that name will always
        # be specified.
        args.name = env.name

    prefix = common.get_prefix(args, search=False)
    # CAN'T Check with this function since it assumes we will create prefix.
    # cli_install.check_prefix(prefix, json=args.json)

    # TODO, add capability
    # common.ensure_override_channels_requires_channel(args)
    # channel_urls = args.channel or ()

    for installer_type, specs in env.dependencies.items():
        try:
            installer = get_installer(installer_type)
            installer.install(prefix, specs, args, env)
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
        cli_install.print_activate(args.name if args.name else prefix)
