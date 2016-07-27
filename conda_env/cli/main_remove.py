from __future__ import absolute_import, print_function
from argparse import RawDescriptionHelpFormatter, Namespace

from conda.cli import common

_help = "Remove an environment"
_description = _help + """

Removes a provided environment.  You must deactivate the existing
environment before you can remove it.
""".lstrip()

_example = """

Examples:

    conda env remove --name FOO
    conda env remove -n FOO
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'remove',
        formatter_class=RawDescriptionHelpFormatter,
        description=_description,
        help=_help,
        epilog=_example,
    )

    common.add_parser_prefix(p)
    common.add_parser_json(p)
    common.add_parser_quiet(p)
    common.add_parser_yes(p)

    p.set_defaults(func=execute)


def execute(args, parser):
    import conda.cli.main_remove
    args = vars(args)
    args.update({
        'all': True, 'channel': None, 'features': None,
        'override_channels': None, 'use_local': None, 'use_cache': None,
        'offline': None, 'force': None, 'pinned': None})
    conda.cli.main_remove.execute(Namespace(**args), parser)
