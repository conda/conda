from argparse import RawDescriptionHelpFormatter
from collections import OrderedDict
import subprocess
import sys
import yaml

from conda import plan
from conda.cli import common, main_list
from conda.cli import install as cli_install
from conda.misc import touch_nonadmin

description = """
Create an environment based on an environment file
"""

example = """
examples:
    conda env create --name=foo --file=env.yml
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )

    common.add_parser_prefix(p)

    p.add_argument(
        '--file',
        required=True
    )
    p.add_argument(
        '-q', '--quiet',
        default=False,
    )
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def conda_installer(prefix, specs, args):
    # TODO: do we need this?
    common.check_specs(prefix, specs, json=args.json)

    # TODO: support all various ways this happens
    index = common.get_index_trap()
    actions = plan.install_actions(prefix, index, specs)
    if plan.nothing_to_do(actions):
        sys.stderr.write('# TODO handle more gracefully')
        sys.exit(-1)

    with common.json_progress_bars(json=args.json and not args.quiet):
        try:
            plan.execute_actions(actions, index, verbose=not args.quiet)
        except RuntimeError as e:
            if len(e.args) > 0 and "LOCKERROR" in e.args[0]:
                error_type = "AlreadyLocked"
            else:
                error_type = "RuntimeError"
            common.exception_and_exit(e, error_type=error_type, json=args.json)
        except SystemExit as e:
            common.exception_and_exit(e, json=args.json)


def pip_installer(prefix, specs, args):
    pip_cmd = main_list.pip_args(prefix) + ['install', ] + specs
    process = subprocess.Popen(pip_cmd, universal_newlines=True)
    process.communicate()


# TODO Make this something that is an external package that uses some
#      sort of entry-point like code so you can install external
#      handlers.
INSTALLERS = {
    'conda': conda_installer,
    'pip': pip_installer,
}


def execute(args, parser):
    command = 'create'
    common.ensure_name_or_prefix(args, command)
    prefix = common.get_prefix(args, search=False)
    cli_install.check_prefix(prefix, json=args.json)

    # TODO, add capability
    # common.ensure_override_channels_requires_channel(args)
    # channel_urls = args.channel or ()

    specs = OrderedDict([('conda', [])])

    with open(args.file, 'rb') as fp:
        data = yaml.load(fp)
    for line in data['dependencies']:
        if type(line) is dict:
            specs.update(line)
        else:
            specs['conda'].append(common.spec_from_line(line))

    for installer_type, specs in specs.items():
        if installer_type not in INSTALLERS:
            raise Exception("Unable to install {}".format(installer_type))

        INSTALLERS[installer_type](prefix, specs, args)

    touch_nonadmin(prefix)
    if not args.json:
        cli_install.print_activate(args.name if args.name else prefix)

