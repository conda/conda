# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.apps.notices import api


def test_display_notices_happy_path(notices_cache_dir_mock):
    """Happy path for displaying notices"""
    api.display_notices()
