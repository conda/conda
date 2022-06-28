# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from argparse import Namespace, ArgumentParser

from ..notices import core as notices


def execute(args: Namespace, _: ArgumentParser):
    """
    Command that retrieves channel notifications, caches them and displays them.
    """
    notices.display_notices()
