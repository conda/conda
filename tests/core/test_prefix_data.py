# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda.base.constants import PREFIX_STATE_FILE
from conda.common.compat import on_win
from conda.core.prefix_data import PrefixData, get_conda_anchor_files_and_records
from conda.exceptions import CorruptedEnvironmentError
from conda.plugins.prefix_data_loaders.pypi import load_site_packages
from conda.testing.helpers import record

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import TmpEnvFixture


ENV_METADATA_DIR = Path(__file__).parent.parent / "data" / "env_metadata"


@pytest.mark.parametrize(
    "path,expected_output",
    [
        pytest.param(
            PATH_TEST_ENV_3 := ENV_METADATA_DIR / "envpy37win",
            {
                "babel",
                "backports-functools-lru-cache",
                "chardet",
                "cheroot",
                "cherrypy",
                "cssselect",
                "dask",
                "django",
                "django-phonenumber-field",
                "django-twilio",
                "entrypoints",
                "h5py",
                "idna",
                "jaraco-functools",
                "lxml",
                "more-itertools",
                "numpy",
                "parsel",
                "phonenumberslite",
                "pluggy",
                "portend",
                "py",
                "pyjwt",
                "pyopenssl",
                "pytz",
                "pywin32",
                "pywin32-ctypes",
                "queuelib",
                "requests",
                "scrapy",
                "service-identity",
                "six",
                "tempora",
                "tox",
                "urllib3",
                "virtualenv",
                "w3lib",
            },
            id=PATH_TEST_ENV_3.name,
            marks=pytest.mark.skipif(not on_win, reason="Windows only"),
        ),
        pytest.param(
            PATH_TEST_ENV_4 := ENV_METADATA_DIR / "envpy27win_whl",
            {
                "asn1crypto",
                "attrs",
                "automat",
                "babel",
                "backports-functools-lru-cache",
                "cffi",
                "chardet",
                "cheroot",
                "cherrypy",
                "configparser",
                "constantly",
                "cryptography",
                "cssselect",
                "dask",
                "django",
                "django-phonenumber-field",
                "django-twilio",
                "entrypoints",
                "enum34",
                "functools32",
                "h5py",
                "hdf5storage",
                "hyperlink",
                "idna",
                "incremental",
                "ipaddress",
                "jaraco-functools",
                "keyring",
                "lxml",
                "more-itertools",
                "numpy",
                "parsel",
                "phonenumberslite",
                "pluggy",
                "portend",
                "py",
                "pyasn1",
                "pyasn1-modules",
                "pycparser",
                "pydispatcher",
                "pyhamcrest",
                "pyjwt",
                "pyopenssl",
                "pytz",
                "pywin32",
                "pywin32-ctypes",
                "queuelib",
                "requests",
                "scrapy",
                "service-identity",
                "six",
                "tempora",
                "tox",
                "twilio",
                "twisted",
                "urllib3",
                "virtualenv",
                "w3lib",
                "zope-interface",
            },
            id=PATH_TEST_ENV_4.name,
            marks=pytest.mark.skipif(not on_win, reason="Windows only"),
        ),
        pytest.param(
            PATH_TEST_ENV_1 := ENV_METADATA_DIR / "envpy27osx",
            {
                "asn1crypto",
                "babel",
                "backports-functools-lru-cache",
                "cffi",
                "chardet",
                "cheroot",
                "cherrypy",
                "configparser",
                "cryptography",
                "cssselect",
                "dask",
                "django",
                "django-phonenumber-field",
                "django-twilio",
                "entrypoints",
                "enum34",
                "h5py",
                "idna",
                "ipaddress",
                "jaraco-functools",
                "lxml",
                "more-itertools",
                "numpy",
                "parsel",
                "phonenumberslite",
                "pip",
                "pluggy",
                "portend",
                "py",
                "pycparser",
                "pyjwt",
                "pyopenssl",
                "pytz",
                "queuelib",
                "requests",
                "scrapy",
                "service-identity",
                "six",
                "tempora",
                "tox",
                "twisted",
                "urllib3",
                "virtualenv",
                "w3lib",
            },
            id=PATH_TEST_ENV_1.name,
            marks=pytest.mark.skipif(on_win, reason="Unix only"),
        ),
        pytest.param(
            PATH_TEST_ENV_2 := ENV_METADATA_DIR / "envpy37osx_whl",
            {
                "asn1crypto",
                "attrs",
                "automat",
                "babel",
                "backports-functools-lru-cache",
                "cffi",
                "chardet",
                "cheroot",
                "cherrypy",
                "constantly",
                "cryptography",
                "cssselect",
                "dask",
                "django",
                "django-phonenumber-field",
                "django-twilio",
                "entrypoints",
                "h5py",
                "hdf5storage",
                "hyperlink",
                "idna",
                "incremental",
                "jaraco-functools",
                "keyring",
                "lxml",
                "more-itertools",
                "numpy",
                "parsel",
                "phonenumberslite",
                "pip",
                "pluggy",
                "portend",
                "py",
                "pyasn1",
                "pyasn1-modules",
                "pycparser",
                "pydispatcher",
                "pyhamcrest",
                "pyjwt",
                "pyopenssl",
                "pysocks",
                "pytz",
                "queuelib",
                "requests",
                "scrapy",
                "service-identity",
                "six",
                "tempora",
                "tox",
                "twilio",
                "twisted",
                "urllib3",
                "virtualenv",
                "w3lib",
                "zope-interface",
            },
            id=PATH_TEST_ENV_2.name,
            marks=pytest.mark.skipif(on_win, reason="Unix only"),
        ),
    ],
)
def test_pip_interop(
    mocker: MockerFixture,
    path: Path,
    expected_output: set[str],
) -> None:
    # test envs with packages installed using either `pip install <pth-to-wheel>` or
    # `python setup.py install`
    mocker.patch("conda.core.prefix_data.rm_rf")

    prefixdata = PrefixData(path, pip_interop_enabled=True)
    prefixdata.load()
    records = load_site_packages(prefixdata.prefix_path, prefixdata._prefix_records)

    assert set(records) == expected_output


def test_get_conda_anchor_files_and_records():
    @dataclass
    class DummyPythonRecord:
        files: list[str]

    valid_records = {
        path: DummyPythonRecord([path])
        for path in (
            "v/site-packages/spam.egg-info/PKG-INFO",
            "v/site-packages/foo.dist-info/RECORD",
            "v/site-packages/bar.egg-info",
        )
    }
    invalid_records = {
        path: DummyPythonRecord([path])
        for path in (
            "v/site-packages/valid-package/_vendor/invalid-now.egg-info/PKG-INFO",
            "i/site-packages/stuff.egg-link",
            "i/spam.egg-info/PKG-INFO",
            "i/foo.dist-info/RECORD",
            "i/bar.egg-info",
            "i/site-packages/spam",
            "i/site-packages/foo",
            "i/site-packages/bar",
        )
    }

    assert (
        get_conda_anchor_files_and_records(
            "v/site-packages",
            [*valid_records.values(), *invalid_records.values()],
        )
        == valid_records
    )


def test_corrupt_unicode_conda_meta_json():
    """Test for graceful failure if a Unicode corrupt file exists in conda-meta."""
    with pytest.raises(CorruptedEnvironmentError):
        PrefixData("tests/data/corrupt/unicode").load()


def test_corrupt_json_conda_meta_json():
    """Test for graceful failure if a JSON corrupt file exists in conda-meta."""
    with pytest.raises(CorruptedEnvironmentError):
        PrefixData("tests/data/corrupt/json").load()


@pytest.fixture
def prefix_data(tmp_env: TmpEnvFixture) -> PrefixData:
    with tmp_env() as prefix:
        (prefix / PREFIX_STATE_FILE).write_text(
            json.dumps(
                {
                    "version": 1,
                    "env_vars": {"ENV_ONE": "one", "ENV_TWO": "you", "ENV_THREE": "me"},
                }
            )
        )
        return PrefixData(prefix)


def test_get_environment_env_vars(prefix_data: PrefixData):
    ex_env_vars = {"ENV_ONE": "one", "ENV_TWO": "you", "ENV_THREE": "me"}
    env_vars = prefix_data.get_environment_env_vars()
    assert ex_env_vars == env_vars


def test_set_unset_environment_env_vars(prefix_data: PrefixData):
    env_vars_one = {
        "ENV_ONE": "one",
        "ENV_TWO": "you",
        "ENV_THREE": "me",
    }
    env_vars_add = {
        "ENV_ONE": "one",
        "ENV_TWO": "you",
        "ENV_THREE": "me",
        "WOAH": "dude",
    }
    prefix_data.set_environment_env_vars({"WOAH": "dude"})
    env_vars = prefix_data.get_environment_env_vars()
    assert env_vars_add == env_vars

    prefix_data.unset_environment_env_vars(["WOAH"])
    env_vars = prefix_data.get_environment_env_vars()
    assert env_vars_one == env_vars


def test_set_unset_environment_env_vars_no_exist(prefix_data: PrefixData):
    env_vars_one = {
        "ENV_ONE": "one",
        "ENV_TWO": "you",
        "ENV_THREE": "me",
    }
    prefix_data.unset_environment_env_vars(["WOAH"])
    env_vars = prefix_data.get_environment_env_vars()
    assert env_vars_one == env_vars


@pytest.mark.parametrize("remove_auth", (True, False))
def test_no_tokens_dumped(tmp_path: Path, remove_auth: bool):
    (tmp_path / "conda-meta").mkdir(parents=True, exist_ok=True)
    (tmp_path / "conda-meta" / "history").touch()
    pkg_record = record(
        channel="fake",
        url="https://conda.anaconda.org/t/some-fake-token/fake/noarch/a-1.0-0.tar.bz2",
    )
    pd = PrefixData(tmp_path)
    pd.insert(pkg_record, remove_auth=remove_auth)

    json_content = (tmp_path / "conda-meta" / "a-1.0-0.json").read_text()
    if remove_auth:
        assert "/t/<TOKEN>/" in json_content
    else:
        assert "/t/some-fake-token/" in json_content


@pytest.mark.parametrize(
    "prefix1,prefix2,equals",
    [
        ("missing", None, False),
        ("missing", "missing", True),
        ("missing", "{path}", False),
        ("{path}", None, False),
        ("{path}", "missing", False),
        ("{path}", "{path}", True),
    ],
)
def test_prefix_data_equality(
    tmp_path: Path,
    prefix1: str,
    prefix2: str | None,
    equals: bool,
) -> None:
    prefix_data1 = PrefixData(prefix1.format(path=tmp_path))
    prefix_data2 = PrefixData(prefix2.format(path=tmp_path)) if prefix2 else prefix2
    assert (prefix_data1 == prefix_data2) is equals
