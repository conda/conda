from argparse import RawDescriptionHelpFormatter

from conda.cli import common

description = """
Attach a Conda environment into a notebook
"""

example = """
examples:
    conda env attach notebook.ipynb
    conda env attach -n darth/deathstar notebook.ipynb
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'attach',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )
    p.add_argument(
        '-n', '--name',
        action='store',
        help='environment definition',
        default=None
    )
    p.add_argument(
        '--force',
        action='store_true',
        default=False,
        help='Replace existing environment definition'
    )
    p.add_argument(
        'notebook',
        help='notebook file',
        action='store',
        default=None
    )
    common.add_parser_json(p)

    p.set_defaults(func=execute)


def execute(args, parser):
    # info_dict = {'envs': []}
    # common.handle_envs_list(info_dict['envs'], not args.json)
    #
    # if args.json:
    #     common.stdout_json(info_dict)
    print(args)
