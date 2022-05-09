# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import time
import logging
from argparse import Namespace, ArgumentParser

from ..base.context import context
from conda import notices

logger = logging.getLogger(__name__)


def timeit(func):
    def wrapper(*args, **kwargs):
        before = time.time()
        resp = func(*args, **kwargs)
        print(f"Total time: {time.time() - before}")
        return resp

    return wrapper


@timeit
def execute(_: Namespace, __: ArgumentParser):
    """
    Command that retrieves channel notifications, caches them and displays them.
    """
    channels = notices.get_channel_objs(context.channels)
    channel_name_urls = notices.get_channel_name_and_urls(channels)
    channel_notice_responses = notices.get_notice_responses(channel_name_urls)
    channel_notices = notices.flatten_notice_responses(channel_notice_responses)

    notices.print_notices(channel_notices)
