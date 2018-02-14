# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

try:
    from requests import ConnectionError, HTTPError, Session
    from requests.adapters import BaseAdapter, HTTPAdapter
    from requests.auth import AuthBase, _basic_auth_str
    from requests.cookies import extract_cookies_to_jar
    from requests.exceptions import InvalidSchema, SSLError
    from requests.hooks import dispatch_hook
    from requests.models import Response
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    from requests.structures import CaseInsensitiveDict
    from requests.utils import get_auth_from_url, get_netrc_auth
except ImportError:  # pragma: no cover
    from pip._vendor.requests import ConnectionError, HTTPError, Session
    from pip._vendor.requests.adapters import BaseAdapter, HTTPAdapter
    from pip._vendor.requests.auth import AuthBase, _basic_auth_str
    from pip._vendor.requests.cookies import extract_cookies_to_jar
    from pip._vendor.requests.exceptions import InvalidSchema, SSLError
    from pip._vendor.requests.hooks import dispatch_hook
    from pip._vendor.requests.models import Response
    from pip._vendor.requests.packages.urllib3.exceptions import InsecureRequestWarning
    from pip._vendor.requests.structures import CaseInsensitiveDict
    from pip._vendor.requests.utils import get_auth_from_url, get_netrc_auth

dispatch_hook = dispatch_hook  # lgtm [py/redundant-assignment]
BaseAdapter = BaseAdapter  # lgtm [py/redundant-assignment]
Response = Response  # lgtm [py/redundant-assignment]
CaseInsensitiveDict = CaseInsensitiveDict  # lgtm [py/redundant-assignment]
Session = Session  # lgtm [py/redundant-assignment]
HTTPAdapter = HTTPAdapter  # lgtm [py/redundant-assignment]
AuthBase = AuthBase  # lgtm [py/redundant-assignment]
_basic_auth_str = _basic_auth_str  # lgtm [py/redundant-assignment]
extract_cookies_to_jar = extract_cookies_to_jar  # lgtm [py/redundant-assignment]
get_auth_from_url = get_auth_from_url  # lgtm [py/redundant-assignment]
get_netrc_auth = get_netrc_auth  # lgtm [py/redundant-assignment]
ConnectionError = ConnectionError  # lgtm [py/redundant-assignment]
HTTPError = HTTPError  # lgtm [py/redundant-assignment]
InvalidSchema = InvalidSchema  # lgtm [py/redundant-assignment]
SSLError = SSLError  # lgtm [py/redundant-assignment]
InsecureRequestWarning = InsecureRequestWarning  # lgtm [py/redundant-assignment]
