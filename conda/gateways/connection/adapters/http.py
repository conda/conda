# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2008-2023 The pip developers
# SPDX-License-Identifier: MIT
#
"""Defines HTTP transport adapter for CondaSession (requests.Session).

Closely derived from pip:

https://github.com/pypa/pip/blob/8c24fd2a80bad21aa29aec02fb48bd89a1e8f5e1/src/pip/_internal/network/session.py#L254

Under the MIT license:

Copyright (c) 2008-2023 The pip developers (see AUTHORS.txt file on the pip repository)

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

from os.path import exists
from typing import TYPE_CHECKING

from .. import DEFAULT_POOLBLOCK
from .. import HTTPAdapter as BaseHTTPAdapter

if TYPE_CHECKING:
    from ssl import SSLContext
    from typing import Any

    from requests.models import PreparedRequest
    from urllib3 import PoolManager, ProxyManager
    from urllib3.connectionpool import HTTPConnectionPool


class _SSLContextAdapterMixin:
    """Mixin to add the ``ssl_context`` constructor argument to HTTP adapters.

    The additional argument is forwarded directly to the pool manager. This allows us
    to dynamically decide what SSL store to use at runtime, which is used to implement
    the optional ``truststore`` backend.
    """

    def __init__(
        self,
        *,
        ssl_context: SSLContext | None = None,
        **kwargs: Any,
    ) -> None:
        self._ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(
        self,
        connections: int,
        maxsize: int,
        block: bool = DEFAULT_POOLBLOCK,
        **pool_kwargs: Any,
    ) -> PoolManager:
        if self._ssl_context is not None:
            pool_kwargs.setdefault("ssl_context", self._ssl_context)
        return super().init_poolmanager(  # type: ignore[misc]
            connections=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )

    def proxy_manager_for(self, proxy: str, **proxy_kwargs: Any) -> ProxyManager:
        # requests' ProxyManager does not inherit init_poolmanager kwargs (#16252).
        if self._ssl_context is not None:
            proxy_kwargs.setdefault("ssl_context", self._ssl_context)
        return super().proxy_manager_for(proxy, **proxy_kwargs)  # type: ignore[misc]

    def build_connection_pool_key_attributes(
        self,
        request: PreparedRequest,
        verify: bool | str,
        cert: str | tuple[str, str] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        host_params, pool_kwargs = super().build_connection_pool_key_attributes(  # type: ignore[misc]
            request, verify, cert
        )
        if self._ssl_context is not None:
            # An explicit CA override must not inherit the native trust roots.
            # None removes the context inherited from the pool manager, including proxies.
            pool_kwargs["ssl_context"] = self._ssl_context if verify is True else None
        return host_params, pool_kwargs

    def get_connection_with_tls_context(
        self,
        request: PreparedRequest,
        verify: bool | str,
        proxies: dict[str, str] | None = None,
        cert: str | tuple[str, str] | None = None,
    ) -> HTTPConnectionPool:
        pool = super().get_connection_with_tls_context(  # type: ignore[misc]
            request, verify, proxies=proxies, cert=cert
        )
        if (
            self._ssl_context is not None
            and verify is True
            and request.url.lower().startswith("https")
            and pool.proxy is not None
            and pool.proxy.scheme == "https"
        ):
            proxy_config = pool.conn_kw["proxy_config"]
            if proxy_config.ssl_context is None:
                # Pools are already separated by the request's TLS settings.
                # HTTPS proxies use a separate TLS context from the target server.
                pool.conn_kw["proxy_config"] = proxy_config._replace(
                    ssl_context=self._ssl_context
                )
        return pool

    def cert_verify(
        self,
        conn: HTTPConnectionPool,
        url: str,
        verify: bool | str,
        cert: str | tuple[str, str] | None,
    ) -> None:
        if (
            self._ssl_context is None
            or verify is not True
            or not url.lower().startswith("https")
        ):
            return super().cert_verify(conn, url, verify, cert)  # type: ignore[misc]

        # The supplied context provides trust roots without Requests' default CA file.
        conn.cert_reqs = "CERT_REQUIRED"
        conn.ca_certs = None
        conn.ca_cert_dir = None
        if cert:
            if isinstance(cert, (str, bytes)):
                conn.cert_file, conn.key_file = cert, None
            else:
                conn.cert_file, conn.key_file = cert
            if conn.cert_file and not exists(conn.cert_file):
                raise OSError(
                    f"Could not find the TLS certificate file, invalid path: {conn.cert_file}"
                )
            if conn.key_file and not exists(conn.key_file):
                raise OSError(
                    f"Could not find the TLS key file, invalid path: {conn.key_file}"
                )


class HTTPAdapter(_SSLContextAdapterMixin, BaseHTTPAdapter):
    pass
