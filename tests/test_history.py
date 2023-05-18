# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from os.path import dirname
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from conda.history import History


@pytest.fixture
def tmp_history(tmp_path: Path) -> History:
    return History(tmp_path)


def test_works_as_context_manager(tmp_history: History):
    assert getattr(tmp_history, "__enter__")
    assert getattr(tmp_history, "__exit__")


def test_calls_update_on_exit(tmp_history: History, mocker: MockerFixture):
    update = mocker.spy(tmp_history, "update")

    with tmp_history:
        assert update.call_count == 0
    assert update.call_count == 1


def test_returns_history_object_as_context_object(
    tmp_history: History,
    mocker: MockerFixture,
):
    with tmp_history as history:
        assert tmp_history == history


def test_empty_history_check_on_empty_env(tmp_history: History, mocker: MockerFixture):
    mock_file_is_empty = mocker.spy(History, "file_is_empty")
    with tmp_history:
        assert mock_file_is_empty.call_count == 0
        assert tmp_history.file_is_empty()
    assert mock_file_is_empty.call_count == 1
    assert not tmp_history.file_is_empty()


def test_parse_on_empty_env(tmp_history: History, mocker: MockerFixture):
    mock_parse = mocker.spy(History, "parse")
    with tmp_history:
        assert mock_parse.call_count == 0
        assert len(tmp_history.parse()) == 0
    assert len(tmp_history.parse()) == 1


@pytest.fixture
def user_requests() -> list[dict]:
    return History(dirname(__file__)).get_user_requests()


def test_len(user_requests: list[dict]):
    assert len(user_requests) == 6


def test_0(user_requests: list[dict]):
    assert user_requests[0] == {
        "cmd": ["conda", "update", "conda"],
        "date": "2016-02-16 13:31:33",
        "unlink_dists": (),
        "link_dists": (),
    }


def test_last(user_requests: list[dict]):
    assert user_requests[-1] == {
        "action": "install",
        "cmd": ["conda", "install", "pyflakes"],
        "date": "2016-02-18 22:53:20",
        "specs": ["pyflakes", "conda", "python 2.7*"],
        "update_specs": ["pyflakes", "conda", "python 2.7*"],
        "unlink_dists": (),
        "link_dists": ["+pyflakes-1.0.0-py27_0"],
    }


@pytest.mark.parametrize(
    "comment,spec",
    [
        # conda version parsing
        pytest.param(
            "# conda version: 4.5.1",
            {"conda_version": "4.5.1"},
            id="conda 4.5.1",
        ),
        pytest.param(
            "# conda version: 4.5.1rc1",
            {"conda_version": "4.5.1rc1"},
            id="conda 4.5.1rc1",
        ),
        pytest.param(
            "# conda version: 4.5.1dev0",
            {"conda_version": "4.5.1dev0"},
            id="conda 4.5.1dev0",
        ),
        # pre 4.4
        pytest.param(
            "# install specs: param >=1.5.1,<2.0",
            {
                "action": "install",
                "specs": ["param >=1.5.1,<2.0"],
                "update_specs": ["param >=1.5.1,<2.0"],
            },
            id="pre 4.4, install one spec",
        ),
        pytest.param(
            "# install specs: param >=1.5.1,<2.0,0packagename >=1.0.0,<2.0",
            {
                "action": "install",
                "specs": ["param >=1.5.1,<2.0", "0packagename >=1.0.0,<2.0"],
                "update_specs": ["param >=1.5.1,<2.0", "0packagename >=1.0.0,<2.0"],
            },
            id="pre 4.4, install two specs",
        ),
        pytest.param(
            "# install specs: python>=3.5.1,jupyter >=1.0.0,<2.0,matplotlib >=1.5.1,<2.0,numpy >=1.11.0,<2.0,pandas >=0.19.2,<1.0,psycopg2 >=2.6.1,<3.0,pyyaml >=3.12,<4.0,scipy >=0.17.0,<1.0",
            {
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
            },
            id="pre 4.4, install many specs",
        ),
        pytest.param(
            "# update specs: _license >=1.0.0,<2.0",
            {
                "action": "update",
                "specs": ["_license >=1.0.0,<2.0"],
                "update_specs": ["_license >=1.0.0,<2.0"],
            },
            id="pre 4.4, update one spec",
        ),
        pytest.param(
            "# update specs: pandas,_license >=1.0.0,<2.0",
            {
                "action": "update",
                "specs": ["pandas", "_license >=1.0.0,<2.0"],
                "update_specs": ["pandas", "_license >=1.0.0,<2.0"],
            },
            id="pre 4.4, update two specs",
        ),
        # post 4.4
        pytest.param(
            """# install specs: ["param[version='>=1.5.1,<2.0']"]""",
            {
                "action": "install",
                "specs": ["param[version='>=1.5.1,<2.0']"],
                "update_specs": ["param[version='>=1.5.1,<2.0']"],
            },
            id="post 4.4, install spec",
        ),
        pytest.param(
            """# update specs: ["param[version='>=1.5.1,<2.0']"]""",
            {
                "action": "update",
                "specs": ["param[version='>=1.5.1,<2.0']"],
                "update_specs": ["param[version='>=1.5.1,<2.0']"],
            },
            id="post 4.4, update spec",
        ),
    ],
)
def test_comment_parsing(comment: str, spec: dict):
    assert History._parse_comment_line(comment) == spec
