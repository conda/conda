# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from logging import getLogger
from typing import NamedTuple

import pytest

from conda.common.url import (
    Url,
    add_username_and_password,
    is_ip_address,
    is_ipv6_address,
    is_url,
    maybe_add_auth,
    path_to_url,
    percent_decode,
    percent_decode_bytes,
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
    port: int | str = None


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

    for attr in exp_url_obj._fields:
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


# --- path_to_url robustness and edge cases ---


def test_path_to_url_file_scheme_ascii():
    """file:// URLs with ASCII only are returned unchanged (no AttributeError on str)."""
    url = "file:///opt/conda/path"
    assert path_to_url(url) == url
    assert path_to_url("file:///C:/Users/conda") == "file:///C:/Users/conda"


def test_path_to_url_file_scheme_non_ascii_raises():
    """file:// URLs with non-ASCII raise ValueError (Python 3: str has no .decode)."""
    with pytest.raises(ValueError, match="Non-ascii not allowed"):
        path_to_url("file:///opt/café/path")
    with pytest.raises(ValueError, match="Non-ascii not allowed"):
        path_to_url("file:///C:/Users/日本語")


def test_path_to_url_empty_raises():
    """Empty path raises ValueError."""
    with pytest.raises(ValueError, match="Not allowed"):
        path_to_url("")


def test_path_to_url_accepts_bytes():
    """path_to_url accepts bytes and decodes as utf-8 for robustness."""
    import os

    p = os.path.abspath(".")
    assert path_to_url(p.encode("utf-8")) == path_to_url(p)
    # Non-utf-8 bytes decoded with replace become file:// URL with U+FFFD; validation still applies.
    with pytest.raises(ValueError, match="Non-ascii not allowed"):
        path_to_url(b"file:///some\xffpath")


@pytest.mark.skipif(
    __import__("sys").platform != "win32",
    reason="Reserved device names (CON, NUL) only trigger OSError on Windows",
)
def test_path_to_url_invalid_path_raises():
    """Invalid or inaccessible path raises ValueError (OSError wrapped)."""
    # On Windows, reserved device names (CON, NUL, etc.) cause OSError from abspath/expanduser.
    with pytest.raises((ValueError, OSError)):
        path_to_url("CON")


# --- percent_decode robustness and edge cases ---


def test_percent_decode_basic():
    """percent_decode decodes %XX to bytes and returns utf-8 decoded string."""
    assert percent_decode("hello%20world") == "hello world"
    assert percent_decode("path%2Fto%2Ffile") == "path/to/file"
    assert percent_decode("no-percent") == "no-percent"


def test_percent_decode_utf8_sequence():
    """Percent-encoded UTF-8 sequences decode correctly."""
    # é as %C3%A9
    assert percent_decode("caf%C3%A9") == "café"
    assert percent_decode("%E6%97%A5") == "日"  # U+65E5


def test_percent_decode_bytes():
    """percent_decode_bytes accepts bytes and is robust to encoding."""
    assert percent_decode_bytes(b"hello%20world") == "hello world"
    assert percent_decode_bytes(b"caf%C3%A9") == "café"
    # Invalid utf-8 uses replace
    result = percent_decode_bytes(b"hello\xff%20world")
    assert "hello" in result and "world" in result


def test_percent_decode_incomplete_at_end():
    """Incomplete percent-encoding at end of string does not crash (edge case)."""
    # Regex only matches %XX so "%" alone or "%1" are not in ranges; no crash.
    assert percent_decode("trailing%") == "trailing%"
    assert percent_decode("trailing%2") == "trailing%2"


# --- Url port validation (robustness / edge cases) ---


def test_url_port_valid():
    """Url accepts valid port as int or str and normalizes to str."""
    u = Url(scheme="http", hostname="example.com", port=8080)
    assert u.port == "8080"
    u2 = Url(scheme="https", hostname="example.com", port="443")
    assert u2.port == "443"


def test_url_port_invalid_raises():
    """Url with invalid port raises ValueError."""
    with pytest.raises(ValueError, match="must be 0-65535"):
        Url(scheme="http", hostname="example.com", port=70000)
    with pytest.raises(ValueError, match="must be 0-65535"):
        Url(scheme="http", hostname="example.com", port=-1)
    with pytest.raises(ValueError, match="must be numeric"):
        Url(scheme="http", hostname="example.com", port="not-a-number")


def test_url_port_none_or_empty():
    """Url with None or empty port is accepted as no port."""
    u = Url(scheme="http", hostname="example.com", port=None)
    assert u.port is None
    u2 = Url(scheme="http", hostname="example.com", port="")
    assert u2.port is None


def test_urlparse_with_port_still_works():
    """urlparse still produces Url with valid port from string."""
    u = urlparse("https://conda.io:443/path")
    assert u.port == "443"
    assert str(u) == "https://conda.io:443/path"
