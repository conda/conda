# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest
import sys


def test_no_ssl(monkeypatch):
    monkeypatch.setitem(sys.modules, "ssl", None)

    from conda.core.subdir_data import fetch_repodata_remote_request
    from conda.exceptions import CondaSSLError

    url = "https://www.fake.fake/fake/fake/noarch"
    etag = None
    mod_stamp = "Mon, 28 Jan 2019 01:01:01 GMT"
    with pytest.raises(CondaSSLError):
        fetch_repodata_remote_request(url, etag, mod_stamp)
