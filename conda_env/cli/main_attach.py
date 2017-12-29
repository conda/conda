from argparse import RawDescriptionHelpFormatter

from conda.cli.conda_argparse import add_parser_json

from .common import get_prefix
from ..env import from_environment
from ..utils.notebooks import Notebook

description = """
WARNING: This command is deprecated in conda 4.4 and scheduled for removal in conda 4.5.

Embeds information describing your conda environment
into the notebook metadata
"""

example = """
examples:
    conda env attach -n base notebook.ipynb
    conda env attach -r user/environment notebook.ipynb
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'attach',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-n', '--name',
        action='store',
        help='local environment definition',
        default=None
    )
    group.add_argument(
        '-r', '--remote',
        action='store',
        help='remote environment definition',
        default=None
    )
    p.add_argument(
        '-p', "--prefix",
        action="store",
        help="Full path to environment prefix",
        metavar='PATH',
        default=None
    )
    p.add_argument(
        '--force',
        action='store_true',
        default=False,
        help='Replace existing environment definition'
    )
    p.add_argument(
        '--no-builds',
        default=False,
        action='store_true',
        required=False,
        help='Remove build specification from dependencies'
    )
    p.add_argument(
        'notebook',
        help='notebook file',
        action='store',
        default=None
    )
    add_parser_json(p)
    p.set_defaults(func='.main_attach.execute')


def execute(args, parser):
    print("WARNING: conda env attach is deprecated and will be removed as part of conda 4.5.")

    if args.prefix is None:
        prefix = get_prefix(args)
    else:
        prefix = args.prefix

    if args.name is not None:
        content = from_environment(args.name, prefix, no_builds=args.no_builds).to_dict()
    else:
        content = {'remote': args.remote}

    print("Environment {} will be attach into {}".format(args.name, args.notebook))
    nb = Notebook(args.notebook)
    if nb.inject(content, args.force):
        print("Done.")
    else:
        print("The environment couldn't be attached due:")
        print(nb.msg)
