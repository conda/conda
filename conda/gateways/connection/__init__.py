# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
try:
    from requests import ConnectionError, HTTPError, Session
    from requests.adapters import BaseAdapter, HTTPAdapter
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
    from pip._vendor.requests import ConnectionError, HTTPError, Session
    from pip._vendor.requests.adapters import BaseAdapter, HTTPAdapter
    from pip._vendor.requests.auth import AuthBase, _basic_auth_str
    from pip._vendor.requests.cookies import extract_cookies_to_jar
    from pip._vendor.requests.exceptions import ChunkedEncodingError, InvalidSchema
    from pip._vendor.requests.exceptions import ProxyError as RequestsProxyError
    from pip._vendor.requests.exceptions import SSLError
    from pip._vendor.requests.hooks import dispatch_hook
    from pip._vendor.requests.models import Response
    from pip._vendor.requests.packages.urllib3.exceptions import InsecureRequestWarning
    from pip._vendor.requests.packages.urllib3.util.retry import Retry
    from pip._vendor.requests.structures import CaseInsensitiveDict
    from pip._vendor.requests.utils import get_auth_from_url, get_netrc_auth


dispatch_hook = dispatch_hook
BaseAdapter = BaseAdapter
Response = Response
CaseInsensitiveDict = CaseInsensitiveDict
Session = Session
HTTPAdapter = HTTPAdapter
AuthBase = AuthBase
_basic_auth_str = _basic_auth_str
extract_cookies_to_jar = extract_cookies_to_jar
get_auth_from_url = get_auth_from_url
get_netrc_auth = get_netrc_auth
ConnectionError = ConnectionError
ChunkedEncodingError = ChunkedEncodingError
HTTPError = HTTPError
InvalidSchema = InvalidSchema
SSLError = SSLError
InsecureRequestWarning = InsecureRequestWarning
RequestsProxyError = RequestsProxyError
Retry = Retry
