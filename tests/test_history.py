# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import unittest
from os.path import dirname
from pathlib import Path
from pprint import pprint
from unittest import mock

import pytest

from conda.history import History
from conda.testing.cases import BaseTestCase
from conda.testing.integration import make_temp_prefix


def test_works_as_context_manager():
    h = History("/path/to/prefix")
    assert getattr(h, "__enter__")
    assert getattr(h, "__exit__")


def test_calls_update_on_exit():
    h = History("/path/to/prefix")
    with mock.patch.object(h, "init_log_file") as init_log_file:
        init_log_file.return_value = None
        with mock.patch.object(h, "update") as update:
            with h:
                assert update.call_count == 0
                pass
        assert update.call_count == 1


def test_returns_history_object_as_context_object():
    h = History("/path/to/prefix")
    with mock.patch.object(h, "init_log_file") as init_log_file:
        init_log_file.return_value = None
        with mock.patch.object(h, "update"):
            with h as h2:
                assert h == h2


def test_empty_history_check_on_empty_env():
    with mock.patch.object(History, "file_is_empty") as mock_file_is_empty:
        with History(make_temp_prefix()) as h:
            assert mock_file_is_empty.call_count == 0
        assert mock_file_is_empty.call_count == 0
        assert h.file_is_empty()
    assert mock_file_is_empty.call_count == 1
    assert not h.file_is_empty()


def test_parse_on_empty_env(tmp_path: Path):
    with mock.patch.object(History, "parse") as mock_parse:
        with History(make_temp_prefix(name=str(tmp_path))) as h:
            assert mock_parse.call_count == 0
            assert len(h.parse()) == 0
    assert len(h.parse()) == 1


@pytest.fixture
def user_requests():
    h = History(dirname(__file__))
    return h.get_user_requests()


def test_len(user_requests):
    assert len(user_requests) == 6


def test_0(user_requests):
    assert user_requests[0] == {
        "cmd": ["conda", "update", "conda"],
        "date": "2016-02-16 13:31:33",
        "unlink_dists": (),
        "link_dists": (),
    }


def test_last(user_requests):
    assert user_requests[-1] == {
        "action": "install",
        "cmd": ["conda", "install", "pyflakes"],
        "date": "2016-02-18 22:53:20",
        "specs": ["pyflakes", "conda", "python 2.7*"],
        "update_specs": ["pyflakes", "conda", "python 2.7*"],
        "unlink_dists": (),
        "link_dists": ["+pyflakes-1.0.0-py27_0"],
    }


def test_conda_comment_version_parsing():
    assert History._parse_comment_line("# conda version: 4.5.1") == {
        "conda_version": "4.5.1"
    }
    assert History._parse_comment_line("# conda version: 4.5.1rc1") == {
        "conda_version": "4.5.1rc1"
    }
    assert History._parse_comment_line("# conda version: 4.5.1dev0") == {
        "conda_version": "4.5.1dev0"
    }


def test_specs_line_parsing_44():
    # New format (>=4.4)
    item = History._parse_comment_line(
        "# update specs: [\"param[version='>=1.5.1,<2.0']\"]"
    )
    pprint(item)
    assert item == {
        "action": "update",
        "specs": [
            "param[version='>=1.5.1,<2.0']",
        ],
        "update_specs": [
            "param[version='>=1.5.1,<2.0']",
        ],
    }


def test_specs_line_parsing_43():
    # Old format (<4.4)
    item = History._parse_comment_line("# install specs: param >=1.5.1,<2.0")
    pprint(item)
    assert item == {
        "action": "install",
        "specs": [
            "param >=1.5.1,<2.0",
        ],
        "update_specs": [
            "param >=1.5.1,<2.0",
        ],
    }

    item = History._parse_comment_line(
        "# install specs: param >=1.5.1,<2.0,0packagename >=1.0.0,<2.0"
    )
    pprint(item)
    assert item == {
        "action": "install",
        "specs": [
            "param >=1.5.1,<2.0",
            "0packagename >=1.0.0,<2.0",
        ],
        "update_specs": [
            "param >=1.5.1,<2.0",
            "0packagename >=1.0.0,<2.0",
        ],
    }

    item = History._parse_comment_line(
        "# install specs: python>=3.5.1,jupyter >=1.0.0,<2.0,matplotlib >=1.5.1,<2.0,numpy >=1.11.0,<2.0,pandas >=0.19.2,<1.0,psycopg2 >=2.6.1,<3.0,pyyaml >=3.12,<4.0,scipy >=0.17.0,<1.0"
    )
    pprint(item)
    assert item == {
        "action": "install",
        "specs": [
            "python>=3.5.1",
            "jupyter >=1.0.0,<2.0",
            "matplotlib >=1.5.1,<2.0",
            "numpy >=1.11.0,<2.0",
            "pandas >=0.19.2,<1.0",
            "psycopg2 >=2.6.1,<3.0",
            "pyyaml >=3.12,<4.0",
            "scipy >=0.17.0,<1.0",
        ],
        "update_specs": [
            "python>=3.5.1",
            "jupyter >=1.0.0,<2.0",
            "matplotlib >=1.5.1,<2.0",
            "numpy >=1.11.0,<2.0",
            "pandas >=0.19.2,<1.0",
            "psycopg2 >=2.6.1,<3.0",
            "pyyaml >=3.12,<4.0",
            "scipy >=0.17.0,<1.0",
        ],
    }

    item = History._parse_comment_line("# install specs: _license >=1.0.0,<2.0")
    pprint(item)
    assert item == {
        "action": "install",
        "specs": [
            "_license >=1.0.0,<2.0",
        ],
        "update_specs": [
            "_license >=1.0.0,<2.0",
        ],
    }

    item = History._parse_comment_line("# install specs: pandas,_license >=1.0.0,<2.0")
    pprint(item)
    assert item == {
        "action": "install",
        "specs": [
            "pandas",
            "_license >=1.0.0,<2.0",
        ],
        "update_specs": [
            "pandas",
            "_license >=1.0.0,<2.0",
        ],
    }
