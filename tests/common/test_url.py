# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.common.url import maybe_add_auth
from logging import getLogger

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
