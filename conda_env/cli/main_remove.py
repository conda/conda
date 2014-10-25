from __future__ import absolute_import, print_function
from argparse import RawDescriptionHelpFormatter
import textwrap

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
    from conda import config, plan
    from conda.install import linked, rm_rf

    prefix = common.get_prefix(args)
    if plan.is_root_prefix(prefix):
        common.error_and_exit('cannot remove root environment,\n'
                              '       add -n NAME or -p PREFIX option',
                              json=args.json,
                              error_type="CantRemoveRoot")

    if prefix == config.default_prefix:
        common.error_and_exit(textwrap.dedent(
            """
            Conda cannot remove the current environment.

            Please deactivate and run conda env remove again.
            """
        ).lstrip())

    # TODO Why do we need an index for removing packages?
    index = common.get_index_trap(json=args.json)


    actions = {
        plan.PREFIX: prefix,
        plan.UNLINK: sorted(linked(prefix))
    }

    if plan.nothing_to_do(actions):
        # TODO Should this automatically remove even *before* confirmation?
        # TODO Should this display an error when removing something that
        #      doesn't exist?
        rm_rf(prefix)

        if args.json:
            common.stdout_json({
                'success': True,
                'actions': actions
            })
        return

    if args.json and args.dry_run:
        common.stdout_json({
            'success': True,
            'dry_run': True,
            'actions': actions
        })
        return

    if not args.json:
        print()
        print("Remove the following packages in environment %s:" % prefix)
        plan.display_actions(actions, index)

    common.confirm_yn(args)
    plan.execute_actions(actions, index, verbose=not args.quiet)
    rm_rf(prefix)

    if args.json:
        common.stdout_json({
            'success': True,
            'actions': actions
        })
