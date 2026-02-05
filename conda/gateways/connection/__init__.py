# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from requests import ConnectionError, HTTPError, Session  # noqa: F401
from requests.adapters import DEFAULT_POOLBLOCK, BaseAdapter, HTTPAdapter  # noqa: F401
from requests.auth import AuthBase, _basic_auth_str  # noqa: F401
from requests.cookies import extract_cookies_to_jar  # noqa: F401
from requests.exceptions import (  # noqa: F401
    ChunkedEncodingError,
    InvalidSchema,
    SSLError,
)
from requests.exceptions import ProxyError as RequestsProxyError  # noqa: F401
from requests.hooks import dispatch_hook  # noqa: F401
from requests.models import PreparedRequest, Response  # noqa: F401
from requests.packages.urllib3.exceptions import InsecureRequestWarning  # noqa: F401
from requests.packages.urllib3.util.retry import Retry  # noqa: F401
from requests.structures import CaseInsensitiveDict  # noqa: F401
from requests.utils import get_auth_from_url, get_netrc_auth  # noqa: F401

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import IO


@runtime_checkable
class DirectDownloadAdapter(Protocol):
    """Protocol for adapters that support optimized direct-to-file downloads.

    Adapters implementing this protocol can bypass the standard streaming path
    and write directly to a file object, avoiding intermediate buffering.
    """

    def download_to_fileobj(
        self,
        url: str,
        fileobj: IO[bytes],
        progress_callback: Callable[[float], None] | None = None,
        size: int | None = None,
    ) -> None:
        """Download directly to a file object.

        :param url: URL to download from
        :param fileobj: File object to write to (binary write mode)
        :param progress_callback: Optional callback(fraction) where fraction is 0.0-1.0
        :param size: Content length (required for progress reporting)
        """
        ...
