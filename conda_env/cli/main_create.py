from argparse import RawDescriptionHelpFormatter
import os
import textwrap
import sys

from conda import config
from conda.cli import common
from conda.cli import install as cli_install
from conda.misc import touch_nonadmin

from ..env import from_file, from_yaml
from ..installers.base import get_installer, InvalidInstaller
from ..specs import all_specs
from .. import exceptions

description = """
Create an environment based on an environment file
"""

example = """
examples:
    conda env create
    conda env create vader/deathstar
    conda env create -f=/path/to/environment.yml
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
    p.add_argument(
        '-n', '--name',
        action='store',
        help='environment definition [Deprecated]',
        default=None,
        dest='old_name'
    )
    p.add_argument(
        '-q', '--quiet',
        action='store_false',
        default=False,
    )
    p.add_argument(
        'name',
        help='environment definition',
        action='store',
        default=None,
        nargs='?'
    )
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):

    if args.name or args.old_name:
        if args.name is not None:
            name = args.name
        else:
            name = args.old_name
            print("`--name` is deprecated. Use:\n"
                  "  conda env create {}".format(args.old_name))

        for Spec in all_specs:
            spec = Spec(name)
            if spec.can_process():
                env = from_yaml(spec.environment)
                args.name = env.name

    else:
        try:
            env = from_file(args.file)
        except exceptions.EnvironmentFileNotFound as e:
            msg = 'Unable to locate environment file: %s\n\n' % e.filename
            msg += "\n".join(textwrap.wrap(textwrap.dedent("""
                Please verify that the above file is present and that you have
                permission read the file's contents.  Note, you can specify the
                file to use by explictly adding --file=/path/to/file when calling
                conda env create.""").lstrip()))

            common.error_and_exit(msg, json=args.json)

    prefix = common.get_prefix(args, search=False)
    cli_install.check_prefix(prefix, json=args.json)

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
