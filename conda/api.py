from __future__ import print_function, division, absolute_import

import os
from collections import defaultdict
from os.path import isdir, join
from operator import itemgetter

from conda import config
from conda import install
from conda.fetch import fetch_index
from conda.compat import iteritems, itervalues
from conda.resolve import Package, Resolve


def get_index(channel_urls=(), prepend=True, platform=None,
              use_cache=False, unknown=False, offline=False,
              prefix=None):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    If prefix is supplied, then the packages installed in that prefix are added.
    """
    channel_urls = config.normalize_urls(channel_urls, platform, offline)
    if prepend:
        pri0 = max(itervalues(channel_urls), key=itemgetter(1))[1] if channel_urls else 0
        for url, rec in iteritems(config.get_channel_urls(platform, offline)):
            channel_urls[url] = (rec[0], rec[1] + pri0)
    index = fetch_index(channel_urls, use_cache=use_cache, unknown=unknown)
    if prefix:
        for dist, info in iteritems(install.linked_data(prefix)):
            fn = dist + '.tar.bz2'
            channel = info.get('channel', '')
            if channel not in channel_urls:
                channel_urls[channel] = (config.canonical_channel_name(channel, True, True), 0)
            url_s, priority = channel_urls[channel]
            key = url_s + '::' + fn if url_s else fn
            if key not in index:
                # only if the package in not in the repodata, use local
                # conda-meta (with 'depends' defaulting to [])
                info.setdefault('depends', [])
                info['fn'] = fn
                info['schannel'] = url_s
                info['channel'] = channel
                info['url'] = channel + fn
                info['priority'] = priority
                index[key] = info
    return index


def get_package_versions(package, offline=False):
    index = get_index(offline=offline)
    r = Resolve(index)
    return r.get_pkgs(package, emptyok=True)
