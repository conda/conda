# SPDX-FileCopyrightText: © 2012 Continuum Analytics, Inc. <http://continuum.io>
# SPDX-FileCopyrightText: © 2017 Anaconda, Inc. <https://www.anaconda.com>
# SPDX-License-Identifier: BSD-3-Clause
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
