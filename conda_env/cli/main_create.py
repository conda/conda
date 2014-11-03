from argparse import RawDescriptionHelpFormatter
from collections import OrderedDict
import os
import textwrap
import sys
import yaml

from conda import config
from conda.cli import common
from conda.cli import install as cli_install
from conda.misc import touch_nonadmin

from ..installers.base import get_installer, InvalidInstaller

description = """
Create an environment based on an environment file
"""

example = """
examples:
    conda env create
    conda env create -n=foo
    conda env create -f=/path/to/environment.yml
    conda env create --name=foo --file=environment.yml
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
        default=False,
    )
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    if not os.path.exists(args.file):
        msg = 'Unable to locate environment file: %s\n\n' % args.file
        msg += "\n".join(textwrap.wrap(textwrap.dedent("""
            Please verify that the above file is present and that you have
            permission read the file's contents.  Note, you can specify the
            file to use by explictly adding --file=/path/to/file when calling
            conda env create.""").lstrip()))

        common.error_and_exit(msg, json=args.json)
    with open(args.file, 'rb') as fp:
        data = yaml.load(fp)

    if not args.name:
        if not 'name' in data:
            # TODO It would be nice to be able to format this more cleanly
            common.error_and_exit(
                'An environment name is required.\n\n'
                'You can either specify one directly with --name or you can add\n'
                'a name property to your %s file.' % args.file,
                json=args.json
            )
        # Note: stubbing out the args object as all of the
        # conda.cli.common code thinks that name will always
        # be specified.
        args.name = data['name']

    prefix = common.get_prefix(args, search=False)
    cli_install.check_prefix(prefix, json=args.json)

    # TODO, add capability
    # common.ensure_override_channels_requires_channel(args)
    # channel_urls = args.channel or ()

    specs = OrderedDict([('conda', [])])

    for line in data['dependencies']:
        if type(line) is dict:
            specs.update(line)
        else:
            specs['conda'].append(common.spec_from_line(line))

    for installer_type, specs in specs.items():
        try:
            installer = get_installer(installer_type)
            installer.install(prefix, specs, args, data)
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

