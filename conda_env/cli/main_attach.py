from argparse import RawDescriptionHelpFormatter
from ..utils.notebooks import current_env, Notebook
from conda.cli import common
from ..env import from_environment


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
    print(args)
    if args.name is None:
        args.name = current_env()
        prefix = common.get_prefix(args)
        content = from_environment(args.name, prefix).to_yaml()
    else:
        content = "name: {}".format(args.name)

    print("Environment {} will be attach into {}".format(args.name, args.notebook))
    nb = Notebook(args.notebook)
    if nb.inject(content, args.force):
        print("Done.")
    else:
        print("The environment couldn't be attached due:")
        print(nb.msg)
