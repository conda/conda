from __future__ import print_function, division, absolute_import

from . import install
from .base.context import context
from .compat import iteritems, itervalues
from .models.channel import prioritize_channels
from .fetch import fetch_index
from .resolve import Resolve

def get_index(channel_urls=(), prepend=True, platform=None,
              use_local=False, use_cache=False, unknown=False, prefix=False):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    If prefix is supplied, then the packages installed in that prefix are added.
    """
    if use_local:
        channel_urls = ['local'] + list(channel_urls)
    if prepend:
        channel_urls += context.channels
    channel_urls = prioritize_channels(channel_urls)
    index = fetch_index(channel_urls, use_cache=use_cache, unknown=unknown)
    if prefix:
        priorities = {c: p for c, p in itervalues(channel_urls)}
        maxp = max(itervalues(priorities)) + 1 if priorities else 1
        for dist, info in iteritems(install.linked_data(prefix)):
            fn = info['fn']
            schannel = info['schannel']
            prefix = '' if schannel == 'defaults' else schannel + '::'
            priority = priorities.get(schannel, maxp)
            key = prefix + fn
            if key in index:
                # Copy the link information so the resolver knows this is installed
                index[key] = index[key].copy()
                index[key]['link'] = info.get('link') or True
            else:
                # only if the package in not in the repodata, use local
                # conda-meta (with 'depends' defaulting to [])
                info.setdefault('depends', [])
                info['priority'] = priority
                index[key] = info
    return index


def get_package_versions(package):
    index = get_index()
    r = Resolve(index)
    return r.get_pkgs(package, emptyok=True)
