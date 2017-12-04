from __future__ import absolute_import, print_function

from argparse import Namespace, RawDescriptionHelpFormatter

from os.path import isdir

from conda.cli.conda_argparse import (add_parser_json, add_parser_prefix, add_parser_quiet,
                                      add_parser_yes)

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

    add_parser_prefix(p)
    add_parser_json(p)
    add_parser_quiet(p)
    add_parser_yes(p)

    p.set_defaults(func='.main_remove.execute')


def execute(args, parser):
    import conda.cli.main_remove
    args = vars(args)
    args.update({
        'all': True, 'channel': None, 'features': None,
        'override_channels': None, 'use_local': None, 'use_cache': None,
        'offline': None, 'force': None, 'pinned': None})
    args = Namespace(**args)
    from conda.base.context import context
    context.__init__(argparse_args=args)

    if not isdir(context.target_prefix):
        from conda.exceptions import EnvironmentLocationNotFound
        raise EnvironmentLocationNotFound(context.target_prefix)

    conda.cli.main_remove.execute(args, parser)
