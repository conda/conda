# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from conda.common.compat import PY2, on_win
from conda.common.url import add_username_and_password, is_ip_address, is_ipv6_address, is_url, \
    maybe_add_auth

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
    assert new_url == "http://usr:some%2A%2Fweird%20pass@www.conda.io:80/some/path.html?query1=1&query2=2"


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
    if not (on_win and PY2):
        assert is_ipv6_address('::1') is True
        assert is_ipv6_address('2001:db8:85a3::370:7334') is True
        assert is_ipv6_address('1234:'*7+'1234') is True

    assert is_ipv6_address('192.168.10.10') is False
    assert is_ipv6_address('1234:' * 8 + '1234') is False


def test_is_ip_address():
    assert is_ip_address('192.168.10.10') is True

    if not (on_win and PY2):
        assert is_ip_address('::1') is True

    assert is_ip_address('www.google.com') is False
