# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda notices`.

Manually retrieves channel notifications, caches them and displays them.
"""
from argparse import ArgumentParser, Namespace

from ..exceptions import CondaError
from ..notices import core as notices


def execute(args: Namespace, _: ArgumentParser):
    """Command that retrieves channel notifications, caches them and displays them."""
    try:
        channel_notice_set = notices.retrieve_notices()
    except OSError as exc:
        raise CondaError(f"Unable to retrieve notices: {exc}")

    notices.display_notices(channel_notice_set)
