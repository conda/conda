from __future__ import absolute_import

from conda.api import get_index
from conda.cli import common
from conda.core.solve import install_actions_list
from conda.models.channel import prioritize_channels


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
    channel_urls = channel_urls + [chan for chan in env.channels if chan != 'nodefaults']
    index = get_index(channel_urls=channel_urls,
                      prepend='nodefaults' not in env.channels,
                      prefix=prefix)
    _channel_priority_map = prioritize_channels(channel_urls)
    unlink_link_transaction = install_actions_list(prefix, index, specs, prune=prune,
                                                   channel_priority_map=_channel_priority_map)

    with common.json_progress_bars(json=args.json and not args.quiet):
        pfe = unlink_link_transaction.get_pfe()
        pfe.execute()
        unlink_link_transaction.execute()
