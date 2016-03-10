from __future__ import absolute_import

from conda.cli import common
from conda import plan


def install(prefix, specs, args, env, prune=False):
    # TODO: do we need this?
    common.check_specs(prefix, specs, json=args.json)

    # TODO: support all various ways this happens
    index = common.get_index_trap(channel_urls=env.channels)
    actions = plan.install_actions(prefix, index, specs, prune=prune)

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
