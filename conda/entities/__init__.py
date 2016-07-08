# -*- coding: utf-8 -*-
"""
Entities are data transfer objects or "light-weight" domain objects with no appreciable logic.
Entities are used to pass data between layers of the stack.

Conda modules importable from ``conda.entities`` are

- ``conda._vendor``
- ``conda.common``
- ``conda.entities``

"""
from __future__ import absolute_import, division, print_function


class Channel(object):

    def __init__(self, value):
        self._raw_value = value

    @property
    def normalized_urls(self):
        return None

    @property
    def canonical_name(self):
        channel = self._raw_value
        channel = remove_binstar_tokens(channel).rstrip('/')
        if any(channel.startswith(i) for i in get_default_urls(True)):
            return 'defaults'
        elif any(channel.startswith(i) for i in get_local_urls(clear_cache=False)):
            return 'local'
        channel_alias = channel_prefix(False)
        if channel.startswith(channel_alias):
            return channel.split(channel_alias, 1)[1]
        elif channel.startswith('http:/'):
            channel2 = 'https' + channel[4:]
            channel3 = canonical_channel_name(channel2)
            return channel3 if channel3 != channel2 else channel
        else:
            return channel



