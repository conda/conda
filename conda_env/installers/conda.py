from __future__ import absolute_import

from conda.cli import common
from conda import plan
from conda.exceptions import LockError, CondaSystemExit, CondaRuntimeError
from conda.api import get_index
from conda.compat import text_type


def install(prefix, specs, args, env, prune=False):
    # TODO: support all various ways this happens
    # Including 'nodefaults' in the channels list disables the defaults
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
    index = get_index(channel_urls=channel_urls + [chan for chan in env.channels
                                                   if chan != 'nodefaults'],
                      prepend='nodefaults' not in env.channels)
    actions = plan.install_actions(prefix, index, specs, prune=prune)

    with common.json_progress_bars(json=args.json and not args.quiet):
        try:
            plan.execute_actions(actions, index, verbose=not args.quiet)
        except RuntimeError as e:
            if len(e.args) > 0 and "LOCKERROR" in e.args[0]:
                raise LockError('Already locked: %s' % text_type(e))
            else:
                raise CondaRuntimeError('RuntimeError: %s' % e)
        except SystemExit as e:
            raise CondaSystemExit('Exiting', e)
