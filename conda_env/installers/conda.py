from __future__ import absolute_import

from conda.cli import common
from conda import plan
from conda_env.cli.common import exception_and_exit, check_specs, get_index_trap

def install(prefix, specs, args, env, prune=False):
    # TODO: do we need this?
    check_specs(prefix, specs, json=args.json)

    new_specs = []
    channel_urls = set()
    for elem in specs:
        if "::" in elem:
            channel_urls.add(elem.split("::")[0])
            new_specs.append(elem.split("::")[-1])
        else:
            new_specs.append(elem)
    specs = new_specs
    channel_urls = list(channel_urls)
    # TODO: support all various ways this happens
    # Including 'nodefaults' in the channels list disables the defaults
    index = get_index_trap(channel_urls=channel_urls + [chan for chan in env.channels
                                                     if chan != 'nodefaults'],
                                  prepend='nodefaults' not in env.channels)
    actions = plan.install_actions(prefix, index, specs, prune=prune)

    with common.json_progress_bars(json=args.json and not args.quiet):
        try:
            plan.execute_actions(actions, index, verbose=not args.quiet)
        except RuntimeError as e:
            if len(e.args) > 0 and "LOCKERROR" in e.args[0]:
                error_type = "AlreadyLocked"
            else:
                error_type = "RuntimeError"
            exception_and_exit(e, error_type=error_type, json=args.json)
        except SystemExit as e:
            exception_and_exit(e, json=args.json)
