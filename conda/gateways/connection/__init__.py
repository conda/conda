# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
try:
    from requests import ConnectionError, HTTPError, Session
    from requests.adapters import DEFAULT_POOLBLOCK, BaseAdapter
    from requests.adapters import HTTPAdapter as BaseHTTPAdapter
    from requests.auth import AuthBase, _basic_auth_str
    from requests.cookies import extract_cookies_to_jar
    from requests.exceptions import ChunkedEncodingError, InvalidSchema
    from requests.exceptions import ProxyError as RequestsProxyError
    from requests.exceptions import SSLError
    from requests.hooks import dispatch_hook
    from requests.models import Response
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    from requests.packages.urllib3.util.retry import Retry
    from requests.structures import CaseInsensitiveDict
    from requests.utils import get_auth_from_url, get_netrc_auth

except ImportError:  # pragma: no cover
    from pip._vendor.requests import ConnectionError, HTTPError, Session  # noqa: F401
    from pip._vendor.requests.adapters import (  # noqa: F401
        DEFAULT_POOLBLOCK,
        BaseAdapter,
    )
    from pip._vendor.requests.adapters import (  # noqa: F401
        HTTPAdapter as BaseHTTPAdapter,
    )
    from pip._vendor.requests.auth import AuthBase, _basic_auth_str  # noqa: F401
    from pip._vendor.requests.cookies import extract_cookies_to_jar  # noqa: F401
    from pip._vendor.requests.exceptions import SSLError  # noqa: F401
    from pip._vendor.requests.exceptions import (  # noqa: F401
        ChunkedEncodingError,
        InvalidSchema,
    )
    from pip._vendor.requests.exceptions import (  # noqa: F401
        ProxyError as RequestsProxyError,
    )
    from pip._vendor.requests.hooks import dispatch_hook  # noqa: F401
    from pip._vendor.requests.models import Response  # noqa: F401
    from pip._vendor.requests.packages.urllib3.exceptions import (  # noqa: F401
        InsecureRequestWarning,
    )
    from pip._vendor.requests.packages.urllib3.util.retry import Retry  # noqa: F401
    from pip._vendor.requests.structures import CaseInsensitiveDict  # noqa: F401
    from pip._vendor.requests.utils import (  # noqa: F401
        get_auth_from_url,
        get_netrc_auth,
    )
