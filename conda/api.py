from __future__ import print_function, division, absolute_import

from . import install
from .compat import iteritems, itervalues
from .config import normalize_urls, prioritize_channels, get_channel_urls, MAX_PRIORITY
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
    channel_urls = normalize_urls(channel_urls, platform)
    if prepend:
        channel_urls.extend(get_channel_urls(platform))
    channel_urls = prioritize_channels(channel_urls)
    index = fetch_index(channel_urls, use_cache=use_cache, unknown=unknown)
    if prefix:
        schannels = {c for c, p in itervalues(channel_urls)}
        maxp = max(p for c, p in itervalues(channel_urls)) if channel_urls else 1
        for dist, info in iteritems(install.linked_data(prefix)):
            fn = info['fn']
            schannel = info['schannel']
            prefix = '' if schannel == 'defaults' else schannel + '::'
            key = prefix + fn
            if key in index:
                # Copy the link information so the resolver knows this is installed
                index[key] = index[key].copy()
                index[key]['link'] = info.get('link') or True
            else:
                # only if the package in not in the repodata, use local
                # conda-meta (with 'depends' defaulting to [])
                info.setdefault('depends', [])
                # If the schannel is known but the package is not in the index, it is
                # because 1) the channel is unavailable offline or 2) the package has
                # been removed from that channel. Either way, we should prefer any
                # other version of the package to this one.
                info['priority'] = MAX_PRIORITY if schannel in schannels else maxp
                index[key] = info
    return index


def get_package_versions(package):
    index = get_index()
    r = Resolve(index)
    return r.get_pkgs(package, emptyok=True)
