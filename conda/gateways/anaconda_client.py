# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
import warnings
from logging import getLogger
from requests import get
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from ..common.io import captured
from ..common.url import is_ip_address, replace_host, replace_path, urlparse

log = getLogger(__name__)


def binstar_load_token(binstar_api_url):
    if not binstar_api_url:
        return None
    try:
        from binstar_client.utils import load_token
        return load_token(binstar_api_url)
    except ImportError:
        log.debug("Cannot get binstar token for %s because anaconda-client is not "
                  "available.", binstar_api_url)
        return None
    except Exception as e:
        log.info("Exception occurred loading binstar token for url %s.\n%r",
                 binstar_api_url, e)
        return None


def get_binstar_client(anaconda_site):
    try:
        from binstar_client.utils import get_server_api
        with captured():
            return get_server_api(site=anaconda_site)
    except ImportError:
        log.debug("Could not import binstar_client.")
        return None


def get_conda_url_from_binstar_api(url):
    # TODO: Need to respect context.offline
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsecureRequestWarning)
            r = get(url, timeout=(3.05, 6.1), headers={'Content-Type': 'application/json'},
                    verify=False)  # We'll respect context.ssl_verify on all other calls
        r.raise_for_status()
        return r.json()['conda_url']
    except Exception as e:  # NOQA
        log.debug("%r", e)
        return None


def get_binstar_server_url_pair(url):
    # Technically this is core logic, but let's keep anaconda_client logic isolated to this module.

    # Step 1. Try url as given
    result = get_conda_url_from_binstar_api(url)
    if result:
        return url, result

    url_parts = urlparse(url)

    # Step 2. Try url with /api prepended to path
    test_url = replace_path(url_parts, '/api' + url_parts.path if url_parts.path else '/api').url
    result = get_conda_url_from_binstar_api(test_url)
    if result:
        return test_url, result

    # Step 3. If host is a domain name (not an IP address), try api.{url}
    if not is_ip_address(url_parts.host):
        test_url = replace_host(url_parts, 'api.' + url_parts.host)
        result = get_conda_url_from_binstar_api(test_url)
        if result:
            return test_url, result

    # Step 4. Replace first occurrence of "conda" with "api"
    #         Note: Dangerous since users could legitimately have /conda in this url
    test_url = re.sub(r'([./])conda([./])', r'\1api\2', url, count=1)
    result = get_conda_url_from_binstar_api(test_url)
    if result:
        return test_url, result

    # Step 5. No options left. The url is not associated with an Anaconda Server API.
    return None, url


def extract_token_from_url(url):
    """
    Examples:
        >>> extract_token_from_url("https://1.2.3.4/t/tk-123-456/path")
        ('https://1.2.3.4/path', 'tk-123-456')
        >>> extract_token_from_url("https://some.domain/api/t/tk-123-456/path")
        ('https://some.domain/api/path', 'tk-123-456')
        >>> extract_token_from_url("https://1.2.3.4/conda/t/tk-123-456/path")
        ('https://1.2.3.4/conda/path', 'tk-123-456')
    """
    _token_match = re.search(r'/t/([a-zA-Z0-9-]+)', url)
    token = _token_match.groups()[0] if _token_match else None
    cleaned_url = url.replace('/t/' + token, '', 1) if token else url
    return cleaned_url, token


def get_binstar_domain_and_token_for_site(anaconda_site):
    bs_client = get_binstar_client(anaconda_site)
    return bs_client.domain, bs_client.token


def get_channel_url_components(channel_url):
    # try to extract a binstar api token from the url
    cleaned_url, token = extract_token_from_url(channel_url)
    if token:
        # a token was given in the channel_url
        # remove it and handle it separately
        binstar_api_url, conda_repo_url = get_binstar_server_url_pair(cleaned_url)
    else:
        # try to get token from anaconda client
        binstar_api_url, conda_repo_url = get_binstar_server_url_pair(channel_url)
        token = binstar_load_token(binstar_api_url)
    return binstar_api_url, conda_repo_url, token


def get_anaconda_site_components(anaconda_site):
    binstar_domain, token = get_binstar_domain_and_token_for_site(anaconda_site)
    binstar_api_url, conda_repo_url = get_binstar_server_url_pair(binstar_domain)
    return binstar_api_url, conda_repo_url, token

