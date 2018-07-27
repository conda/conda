# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from ..common.compat import with_metaclass
from ..models.channel import Channel


class ChannelDataType(type):

    def __call__(cls, channel):
        assert channel.subdir
        assert not channel.package_filename
        assert type(channel) is Channel
        cache_key = ChannelData.cache_key(channel)
        if not cache_key.startswith('file://') and cache_key in ChannelData._cache_:
            return ChannelData._cache_[cache_key]

        subdir_data_instance = super(ChannelDataType, cls).__call__(channel)
        ChannelData._cache_[cache_key] = subdir_data_instance
        return subdir_data_instance


@with_metaclass(ChannelDataType)
class ChannelData(object):
    _cache_ = {}

    def load(self):
        pass
