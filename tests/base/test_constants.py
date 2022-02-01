# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from conda.base.constants import ChannelPriority
from conda.common.constants import NULL
from logging import getLogger

log = getLogger(__name__)


def test_null_is_falsey():
    assert not NULL


def test_ChannelPriority():
    assert ChannelPriority("strict") == ChannelPriority.STRICT
    assert ChannelPriority["STRICT"] == ChannelPriority.STRICT
    assert ChannelPriority(False) == ChannelPriority.DISABLED
    assert ChannelPriority('false') == ChannelPriority.DISABLED
