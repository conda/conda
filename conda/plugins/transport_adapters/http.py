# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""The default HTTP/HTTPS transport adapter plugins"""
from ... import CondaError
from ...base.context import context
from ...gateways.connection import Retry
from ...gateways.connection.adapters.http import HTTPAdapter
from .. import CondaTransportAdapter, hookimpl


@hookimpl
def conda_transport_adapters():
    ssl_context = None
    if context.ssl_verify == "truststore":
        try:
            import ssl

            import truststore

            ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except ImportError:
            raise CondaError(
                "The `ssl_verify: truststore` setting is only supported on"
                + "Python 3.10 or later."
            )
        # making sure we verify now that we know truststore is enabled
        context.ssl_verify = True

    # Configure retries
    retry = Retry(
        total=context.remote_max_retries,
        backoff_factor=context.remote_backoff_factor,
        status_forcelist=[413, 429, 500, 503],
        raise_on_status=False,
        respect_retry_after_header=False,
    )
    http_adapter = HTTPAdapter(max_retries=retry, ssl_context=ssl_context)
    yield CondaTransportAdapter(name="http", scheme="http", adapter=http_adapter)
    yield CondaTransportAdapter(name="https", scheme="https", adapter=http_adapter)
