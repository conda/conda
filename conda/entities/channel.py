# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from logging import getLogger

from ..base.context import binstar, subdir, context
from os.path import exists
from ..utils import url_path

log = getLogger(__name__)


def get_local_urls():
    # Note, get_*_urls() return unnormalized urls.
    try:
        from conda_build.config import croot
        if exists(croot):
            return [url_path(croot)]
    except ImportError:
        pass
    return []





def _get_rc_urls():
    # Note, get_*_urls() return unnormalized urls.
    if rc is None or rc.get('channels') is None:
        return []
    if 'system' in rc['channels']:
        raise CondaRuntimeError("system cannot be used in .condarc")
    return rc['channels']


def has_scheme(value):
    return '://' in value

def could_be_abspath(value):
    if on_win:
        regex = r'^[a-zA-Z]:[\\/]|^\\|^~|^/'
    else:
        regex = r'^~|^/'
    return bool(re.match(regex, value))


class Channel(object):
    """
    Examples:

    types:
      - url: has_scheme
      - local path
      - just a name

    """


    def __init__(self, value):
        if value == 'defaults':
            raise RuntimeError
        self._raw_value = value

    # @property
    # def normalized_urls(self):
    #     return None

    @property
    def canonical_name(self):

        # is it in defaults?

        # now strip http:// and https:// and trailing /
        # is it the local channel?
        # is it a binstar channel?
        # is it a url?

        channel = self._raw_value
        if channel is None:
            return '<unknown>'
        channel = binstar.remove_binstar_tokens(channel).rstrip('/')
        if any(channel.startswith(i) for i in get_default_urls(True)):
            return 'defaults'
        elif any(channel.startswith(i) for i in get_local_urls()):
            return 'local'
        channel_alias = binstar.channel_prefix(False)
        if channel.startswith(channel_alias):
            return channel.split(channel_alias, 1)[1]
        elif channel.startswith('http:/'):
            channel2 = 'https' + channel[4:]
            channel3 = binstar.canonical_channel_name(channel2)
            return channel3 if channel3 != channel2 else channel
        else:
            return channel

    @property
    def url(self):
        channel = self._raw_value
        if channel is None:
            return None
        if channel == 'local':
            return get_local_urls()
        if channel == 'defaults':
            return context.default_channels



    @staticmethod
    def url_channel(url):
        parts = (url or '').rsplit('/', 2)
        if len(parts) == 1:
            return '<unknown>', '<unknown>'
        if len(parts) == 2:
            return parts[0], parts[0]
        if url.startswith('file://') and parts[1] not in ('noarch', subdir):
            # Explicit file-based URLs are denoted with a '/' in the schannel
            channel = parts[0] + '/' + parts[1]
            schannel = channel + '/'
        else:
            channel = parts[0]
            schannel = Channel(channel).canonical_name
        return channel, schannel

    @staticmethod
    def prioritize_channels(channels):
        newchans = OrderedDict()
        priority = 0
        schans = {}
        for channel in channels:
            channel = channel.rstrip('/') + '/'
            if channel not in newchans:
                channel_s = canonical_channel_name(channel.rsplit('/', 2)[0])
                if channel_s not in schans:
                    priority += 1
                    schans[channel_s] = priority
                newchans[channel] = (channel_s, schans[channel_s])
        return newchans

    @staticmethod
    def normalize_urls(urls, platform=None):
        defaults = tuple(x.rstrip('/') + '/' for x in get_default_urls(False))
        newurls = []
        while urls:
            url = urls[0]
            urls = urls[1:]
            if url == "system" and rc_path:
                urls = get_rc_urls() + urls
                continue
            elif url in ("defaults", "system"):
                t_urls = defaults
            elif url == "local":
                t_urls = get_local_urls()
            else:
                t_urls = [url]
            for url0 in t_urls:
                url0 = url0.rstrip('/')
                if not is_url(url0):
                    url0 = channel_prefix(True) + url0
                else:
                    url0 = add_binstar_tokens(url0)
                for plat in (platform or subdir, 'noarch'):
                    newurls.append('%s/%s/' % (url0, plat))
        return newurls

    @staticmethod
    def get_channel_urls(platform=None):
        if os.getenv('CIO_TEST'):
            import cio_test
            base_urls = cio_test.base_urls
        elif 'channels' in rc:
            base_urls = ['system']
        else:
            base_urls = ['defaults']
        res = normalize_urls(base_urls, platform)
        return res