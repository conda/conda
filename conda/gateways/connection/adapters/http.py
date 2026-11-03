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

from typing import TYPE_CHECKING

from .. import DEFAULT_POOLBLOCK
from .. import HTTPAdapter as BaseHTTPAdapter

if TYPE_CHECKING:
    from ssl import SSLContext
    from typing import Any

    from requests.models import PreparedRequest, Response
    from urllib3 import ProxyManager
    from urllib3.connectionpool import HTTPConnectionPool


class _SSLContextAdapter(BaseHTTPAdapter):
    """Adapter for verified HTTPS requests using the supplied certificate store."""

    def __init__(self, ssl_context: SSLContext, **kwargs: Any) -> None:
        self._ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(
        self,
        connections: int,
        maxsize: int,
        block: bool = DEFAULT_POOLBLOCK,
        **pool_kwargs: Any,
    ) -> None:
        pool_kwargs.setdefault("ssl_context", self._ssl_context)
        super().init_poolmanager(
            connections=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )

    def proxy_manager_for(self, proxy: str, **proxy_kwargs: Any) -> ProxyManager:
        proxy_kwargs.setdefault("ssl_context", self._ssl_context)
        if proxy.lower().startswith("https://"):
            proxy_kwargs.setdefault("proxy_ssl_context", self._ssl_context)
        return super().proxy_manager_for(proxy, **proxy_kwargs)

    def cert_verify(
        self,
        conn: HTTPConnectionPool,
        url: str,
        verify: bool | str,
        cert: str | tuple[str, str] | None,
    ) -> None:
        # Requests >=2.32.5 already sets CERT_REQUIRED and client certificates in
        # the pool. The supplied context provides roots without a certifi file.
        pass


class HTTPAdapter(BaseHTTPAdapter):
    """Keep native certificate trust separate from explicit Requests TLS settings."""

    def __init__(self, *, ssl_context: SSLContext | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ssl_context_adapter = (
            _SSLContextAdapter(ssl_context, **kwargs)
            if ssl_context is not None
            else None
        )

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: Any = None,
        verify: bool | str = True,
        cert: str | tuple[str, str] | None = None,
        proxies: dict[str, str] | None = None,
    ) -> Response:
        # Requests has merged request, session, and environment settings before
        # dispatch. Custom CA paths and disabled verification use ordinary TLS.
        send = super().send
        if (
            self._ssl_context_adapter is not None
            and verify is True
            and request.url.lower().startswith("https://")
        ):
            send = self._ssl_context_adapter.send
        return send(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )

    def close(self) -> None:
        super().close()
        if self._ssl_context_adapter is not None:
            self._ssl_context_adapter.close()
