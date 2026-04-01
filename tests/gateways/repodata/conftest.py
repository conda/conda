# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Expose shard test fixtures from test_shards to sibling modules (e.g. test_shards_subset).
"""

pytest_plugins = ("tests.gateways.repodata.test_shards",)
