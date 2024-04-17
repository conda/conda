# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""A FTP transport adapter"""

from ...gateways.connection.adapters.ftp import FTPAdapter
from .. import CondaTransportAdapter, hookimpl


@hookimpl
def conda_transport_adapters():
    yield CondaTransportAdapter(name="ftp", scheme="ftp", adapter=FTPAdapter)
