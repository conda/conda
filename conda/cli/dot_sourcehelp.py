from __future__ import absolute_import, print_function
import sys


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('..sourcehelp')
    p.add_argument(
        "--deactivate",
        action="store_true"
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    if args.deactivate:
        sys.exit("""Usage: source deactivate

removes the 'bin' directory of the environment activated with 'source
activate' from PATH. """)
    else:
        sys.exit("""Usage: source activate ENV

adds the 'bin' directory of the environment ENV to the front of PATH.
ENV may either refer to just the name of the environment, or the full
prefix path.""")
