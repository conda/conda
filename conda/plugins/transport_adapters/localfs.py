# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""The local filesystem transport adapter plugin"""
from ...gateways.connection.adapters.localfs import LocalFSAdapter
from .. import CondaTransportAdapter, hookimpl


@hookimpl(tryfirst=True)
def conda_transport_adapters():
    yield CondaTransportAdapter(name="localfs", prefix="file://", adapter=LocalFSAdapter)
