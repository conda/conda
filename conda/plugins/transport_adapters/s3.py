# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from ...gateways.connection.adapters.s3 import S3Adapter
from .. import CondaTransportAdapter, hookimpl


@hookimpl
def conda_transport_adapters():
    yield CondaTransportAdapter(name="s3", prefix="s3://", adapter=S3Adapter())
