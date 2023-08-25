# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from logging import getLogger
from typing import NamedTuple, Union

import pytest

from conda.common.url import (
    Url,
    add_username_and_password,
    is_ip_address,
    is_ipv6_address,
    is_url,
    maybe_add_auth,
    split_scheme_auth_token,
    url_to_s3_info,
    urlparse,
)

log = getLogger(__name__)


def test_maybe_add_auth():
    url = "http://www.conda.io:80/some/path.html?query1=1&query2=2"
    new_url = maybe_add_auth(url, "usr:ps")
    assert new_url == "http://usr:ps@www.conda.io:80/some/path.html?query1=1&query2=2"

    url = "http://www.conda.io:80/some/path.html?query1=1&query2=2"
    new_url = maybe_add_auth(url, "usr:ps", force=True)
    assert new_url == "http://usr:ps@www.conda.io:80/some/path.html?query1=1&query2=2"

    url = "http://usr2:ps2@www.conda.io:80/some/path.html?query1=1&query2=2"
    new_url = maybe_add_auth(url, "usr:ps")
    assert new_url == "http://usr2:ps2@www.conda.io:80/some/path.html?query1=1&query2=2"

    url = "http://usr2:ps2@www.conda.io:80/some/path.html?query1=1&query2=2"
    new_url = maybe_add_auth(url, "usr:ps", force=True)
    assert new_url == "http://usr:ps@www.conda.io:80/some/path.html?query1=1&query2=2"


def test_add_username_and_pass_to_url():
    url = "http://www.conda.io:80/some/path.html?query1=1&query2=2"
    new_url = add_username_and_password(url, "usr", "some*/weird pass")
    assert (
        new_url
        == "http://usr:some%2A%2Fweird%20pass@www.conda.io:80/some/path.html?query1=1&query2=2"
    )


def test_is_url():
    assert is_url("http://usr2:ps2@www.conda.io:80/some/path.html?query1=1&query2=2")
    assert is_url("s3://some/bucket.name")
    assert is_url("file:///some/local/path")

    assert not is_url("../../../some/relative/path")
    assert not is_url("/some/absolute/path")
    assert not is_url("another_path.tar.bz2")
    assert not is_url("just-a-directory-maybe")
    assert not is_url("~/.ssh/super-secret")


def test_is_ipv6_address():
    assert is_ipv6_address("::1") is True
    assert is_ipv6_address("2001:db8:85a3::370:7334") is True
    assert is_ipv6_address("1234:" * 7 + "1234") is True
    assert is_ipv6_address("192.168.10.10") is False
    assert is_ipv6_address("1234:" * 8 + "1234") is False


def test_is_ip_address():
    assert is_ip_address("192.168.10.10") is True
    assert is_ip_address("::1") is True
    assert is_ip_address("www.google.com") is False


class UrlTest(NamedTuple):
    """simplified test version of Url object; mainly used for passing in groups of test parameters"""

    scheme: str = ""
    path: str = ""
    query: str = ""
    fragment: str = ""
    username: str = None
    password: str = None
    hostname: str = None
    port: Union[int, str] = None


URLPARSE_TEST_DATA = [
    (
        "192.168.1.1:8080/path/to/resource",
        UrlTest(scheme="", hostname="192.168.1.1", port=8080, path="/path/to/resource"),
    ),
    (
        "https://conda.io/happy/path",
        UrlTest(scheme="https", hostname="conda.io", path="/happy/path"),
    ),
    ("file:///opt/happy/path", UrlTest(scheme="file", path="/opt/happy/path")),
    (
        "https://u:p@conda.io/t/x1029384756/more/path",
        UrlTest(
            scheme="https",
            hostname="conda.io",
            path="/t/x1029384756/more/path",
            username="u",
            password="p",
        ),
    ),
]


@pytest.mark.parametrize("test_url_str,exp_url_obj", URLPARSE_TEST_DATA)
def test_urlparse(test_url_str, exp_url_obj):
    """Tests a variety of different use cases for `conda.common.url.urlparse`."""
    answer = urlparse(test_url_str)

    for attr in exp_url_obj.__annotations__.keys():
        assert getattr(answer, attr) == getattr(exp_url_obj, attr)

    assert str(answer) == test_url_str


URL_OBJ_UNPARSE_DATA = [
    (
        UrlTest(scheme="http", hostname="conda.io", path="/path/to/somewhere"),
        "http://conda.io/path/to/somewhere",
    ),
    (
        UrlTest(
            scheme="https",
            hostname="conda.io",
            username="user",
            password="pass",
            path="/path/to/somewhere",
        ),
        "https://user:pass@conda.io/path/to/somewhere",
    ),
    (UrlTest(scheme="file", path="/opt/happy/path"), "file:///opt/happy/path"),
    (
        UrlTest(scheme="file", path="path/to/something.txt"),
        "file:///path/to/something.txt",
    ),
]


@pytest.mark.parametrize("test_url_obj, expected_url", URL_OBJ_UNPARSE_DATA)
def test_url_obj_unparse(test_url_obj, expected_url):
    """Tests the variety of object instantiations for the `conda.common.url.Url`."""
    url_obj = Url(*test_url_obj)

    assert str(url_obj) == expected_url


def test_split_scheme_auth_token():
    answer = split_scheme_auth_token("https://u:p@conda.io/t/x1029384756/more/path")
    assert answer == ("conda.io/more/path", "https", "u:p", "x1029384756")


def test_url_to_s3_info():
    answer = url_to_s3_info("s3://bucket-name.bucket/here/is/the/key")
    assert answer == ("bucket-name.bucket", "/here/is/the/key")
