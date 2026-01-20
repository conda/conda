# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda.base.constants import PREFIX_PINNED_FILE, PREFIX_STATE_FILE
from conda.common.compat import on_win
from conda.core.prefix_data import PrefixData, get_conda_anchor_files_and_records
from conda.exceptions import CondaError, CorruptedEnvironmentError
from conda.models.enums import PackageType
from conda.models.match_spec import MatchSpec
from conda.plugins.prefix_data_loaders.pypi import load_site_packages
from conda.testing.helpers import record

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import CondaCLIFixture, PipCLIFixture, TmpEnvFixture


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
        pytest.param(
            PATH_TEST_ENV_3 := ENV_METADATA_DIR / "envpy313tosx_whl",
            {
                "imagesize",
            },
            id=PATH_TEST_ENV_3.name,
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
    mocker.patch("conda.plugins.prefix_data_loaders.pypi.rm_rf")

    prefixdata = PrefixData(path, interoperability=True)
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


def test_warn_setting_reserved_env_vars(prefix_data: PrefixData):
    warning_message = r"WARNING: the given environment variable\(s\) are reserved and will be ignored: PATH.+"
    with pytest.warns(UserWarning, match=warning_message):
        prefix_data.set_environment_env_vars({"PATH": "very naughty"})

    # Ensure the PATH is still set in the env vars
    env_vars = prefix_data.get_environment_env_vars()
    assert env_vars.get("PATH") == "very naughty"


def test_unset_reserved_env_vars(prefix_data: PrefixData):
    # Setup prefix data with reserved env var
    with pytest.warns(UserWarning):
        prefix_data.set_environment_env_vars({"PATH": "very naughty"})

    prefix_data.unset_environment_env_vars(["PATH"])
    # Ensure that the PATH is fully removed from the state tile
    env_state_file = prefix_data._get_environment_state_file()
    assert "PATH" not in env_state_file.get("env_vars", {})


@pytest.mark.parametrize("remove_auth", (True, False))
def test_no_tokens_dumped(empty_env: Path, remove_auth: bool):
    pkg_record = record(
        channel="fake",
        url="https://conda.anaconda.org/t/some-fake-token/fake/noarch/a-1.0-0.tar.bz2",
    )
    pd = PrefixData(empty_env)
    pd.insert(pkg_record, remove_auth=remove_auth)

    json_content = (empty_env / "conda-meta" / "a-1.0-0.json").read_text()
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


def test_prefix_insertion_error(
    tmp_env: TmpEnvFixture, test_recipes_channel: str
) -> None:
    """
    Ensure that the right error message is displayed when trying to insert a prefix record
    that already exists in the prefix.
    """
    package_name = "small-executable"
    with tmp_env(package_name) as prefix:
        prefix_data = PrefixData(prefix)

        expected_error_message = (
            f"Prefix record '{package_name}' already exists. "
            f"Try `conda clean --all` to fix."
        )

        with pytest.raises(CondaError, match=expected_error_message):
            prefix_data.insert(
                record(
                    name=package_name,
                    version="1.0.0",
                    build="0",
                    build_number=0,
                    channel="test-channel",
                )
            )


def test_get_conda_packages_returns_sorted_list(
    tmp_env: TmpEnvFixture, test_recipes_channel: str
):
    """Test that get_conda_packages returns conda packages sorted alphabetically."""
    # Create environment with known conda package
    with tmp_env("small-executable") as prefix:
        prefix_data = PrefixData(prefix)
        conda_packages = prefix_data.get_conda_packages()

        # Should return a list
        assert isinstance(conda_packages, list)

        # Should have at least the small-executable package
        assert len(conda_packages) > 0, "Should have at least one conda package"

        # Should be sorted alphabetically
        package_names = [pkg.name for pkg in conda_packages]
        assert package_names == sorted(package_names), (
            "Conda packages should be sorted alphabetically"
        )

        # Should include our test package
        package_names_set = set(package_names)
        assert "small-executable" in package_names_set, (
            "Should include small-executable package"
        )

        # All should be conda packages (not Python packages)
        for pkg in conda_packages:
            assert pkg.package_type in {
                None,
                PackageType.NOARCH_GENERIC,
                PackageType.NOARCH_PYTHON,
            }, (
                f"Package {pkg.name} should be a conda package type, got {pkg.package_type}"
            )


def test_get_python_packages_basic_functionality(
    tmp_env: TmpEnvFixture, test_recipes_channel: str
):
    """Test that get_python_packages returns correct structure even with no Python packages."""
    # Create environment with conda package
    with tmp_env("small-executable") as prefix:
        prefix_data = PrefixData(prefix)
        python_packages = prefix_data.get_python_packages()

        # Should return a list
        assert isinstance(python_packages, list)

        # This test environment likely has no Python packages, which is fine
        # The important thing is that the method works and returns the right structure

        # If there are Python packages, they should be sorted
        if python_packages:
            package_names = [pkg.name for pkg in python_packages]
            assert package_names == sorted(package_names), (
                "Python packages should be sorted alphabetically"
            )

            # All should be Python packages
            for pkg in python_packages:
                assert pkg.package_type in {
                    PackageType.VIRTUAL_PYTHON_WHEEL,
                    PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE,
                    PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE,
                }, (
                    f"Package {pkg.name} should be a Python package type, got {pkg.package_type}"
                )


def test_get_packages_behavior_with_interoperability(
    tmp_env: TmpEnvFixture, pip_cli: PipCLIFixture, wheelhouse: Path
):
    """Test that package extraction behaves correctly with interoperability settings."""
    # Create environment with conda packages and pip
    packages = ["python=3.10", "pip", "ca-certificates"]
    with tmp_env(*packages) as prefix:
        # Install small-python-package wheel for testing pip interoperability
        wheel_path = wheelhouse / "small_python_package-1.0.0-py3-none-any.whl"
        pip_stdout, pip_stderr, pip_code = pip_cli(
            "install", str(wheel_path), prefix=prefix
        )
        assert pip_code == 0, f"pip install failed: {pip_stderr}"

        # Clear prefix data cache to ensure fresh data
        PrefixData._cache_.clear()

        # Enable pip interoperability to detect Python packages
        prefix_data = PrefixData(prefix, interoperability=True)

        # Test all methods together
        conda_packages = prefix_data.get_conda_packages()
        python_packages = prefix_data.get_python_packages()

        # Should have multiple conda packages
        assert len(conda_packages) >= 3, (
            f"Should have at least 3 conda packages, got {len(conda_packages)}"
        )

        # Should have 1 Python package now (small-python-package)
        assert len(python_packages) == 1, (
            f"Should have 1 Python package after installing small-python-package, got {len(python_packages)}"
        )

        # Verify consistency
        assert conda_packages == conda_packages
        assert python_packages == python_packages

        # Check that our test packages are included
        conda_names = {pkg.name for pkg in conda_packages}
        assert "python" in conda_names, "Should include python"
        assert "ca-certificates" in conda_names, "Should include ca-certificates"

        # Check that small-python-package is included in Python packages
        python_names = {pkg.name for pkg in python_packages}
        assert "small-python-package" in python_names, (
            f"Should include small-python-package in Python packages: {python_names}"
        )

        # Verify alphabetical sorting
        conda_names_list = [pkg.name for pkg in conda_packages]
        assert conda_names_list == sorted(conda_names_list), (
            "Conda packages should be sorted"
        )

        # Verify Python packages sorting and structure
        python_names_list = [pkg.name for pkg in python_packages]
        assert python_names_list == sorted(python_names_list), (
            "Python packages should be sorted"
        )

        # Verify all Python packages have correct types
        for pkg in python_packages:
            assert pkg.package_type in {
                PackageType.VIRTUAL_PYTHON_WHEEL,
                PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE,
                PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE,
            }, (
                f"Package {pkg.name} should be a Python package type, got {pkg.package_type}"
            )


def test_package_methods_with_required_python_packages(mocker):
    """Test package extraction methods when Python packages must be found."""
    # Create mock records - some conda, some Python
    conda_record1 = mocker.Mock()
    conda_record1.name = "conda-package-a"
    conda_record1.package_type = PackageType.NOARCH_GENERIC

    conda_record2 = mocker.Mock()
    conda_record2.name = "conda-package-b"
    conda_record2.package_type = PackageType.NOARCH_PYTHON

    python_record1 = mocker.Mock()
    python_record1.name = "python-package-1"
    python_record1.package_type = PackageType.VIRTUAL_PYTHON_WHEEL

    python_record2 = mocker.Mock()
    python_record2.name = "python-package-2"
    python_record2.package_type = PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE

    # Create a mock PrefixGraph that returns both conda and Python packages
    mock_graph = mocker.Mock()
    mock_graph.graph = [conda_record1, conda_record2, python_record1, python_record2]

    # Create a mock PrefixData instance
    mock_prefix_data = mocker.Mock(spec=PrefixData)

    # Monkeypatch the methods to use our mock data
    mock_prefix_data.get_conda_packages = PrefixData.get_conda_packages.__get__(
        mock_prefix_data
    )
    mock_prefix_data.get_python_packages = PrefixData.get_python_packages.__get__(
        mock_prefix_data
    )

    # Mock the iter_records and PrefixGraph
    mock_prefix_data.iter_records.return_value = [
        conda_record1,
        conda_record2,
        python_record1,
        python_record2,
    ]
    mocker.patch("conda.core.prefix_data.PrefixGraph", return_value=mock_graph)

    # Test the methods
    conda_packages = mock_prefix_data.get_conda_packages()
    python_packages = mock_prefix_data.get_python_packages()

    # Test conda packages
    assert len(conda_packages) == 2, "Should have 2 conda packages"
    assert [pkg.name for pkg in conda_packages] == [
        "conda-package-a",
        "conda-package-b",
    ]

    # Test Python packages - NOW WE REQUIRE THEM
    assert len(python_packages) == 2, (
        f"Should have exactly 2 Python packages, got {len(python_packages)}"
    )
    assert [pkg.name for pkg in python_packages] == [
        "python-package-1",
        "python-package-2",
    ]

    # Verify all Python packages have correct types
    for pkg in python_packages:
        assert pkg.package_type in {
            PackageType.VIRTUAL_PYTHON_WHEEL,
            PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE,
            PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE,
        }, f"Package {pkg.name} should be a Python package type, got {pkg.package_type}"


def test_empty_environment_package_methods(tmp_env: TmpEnvFixture):
    """Test package extraction methods with an empty environment."""
    # Create empty environment
    with tmp_env() as prefix:
        prefix_data = PrefixData(prefix)

        conda_packages = prefix_data.get_conda_packages()
        python_packages = prefix_data.get_python_packages()

        # All should be empty lists but still valid
        assert isinstance(conda_packages, list)
        assert isinstance(python_packages, list)
        assert len(conda_packages) == 0, (
            "Empty environment should have no conda packages"
        )
        assert len(python_packages) == 0, (
            "Empty environment should have no python packages"
        )


@pytest.mark.parametrize(
    "method_name,expected_types",
    [
        (
            "get_conda_packages",
            {None, PackageType.NOARCH_GENERIC, PackageType.NOARCH_PYTHON},
        ),
        (
            "get_python_packages",
            {
                PackageType.VIRTUAL_PYTHON_WHEEL,
                PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE,
                PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE,
            },
        ),
    ],
)
def test_package_extraction_methods_types(
    tmp_env: TmpEnvFixture,
    test_recipes_channel: str,
    method_name: str,
    expected_types: set,
):
    """Test that package extraction methods return packages of expected types."""
    with tmp_env("small-executable") as prefix:
        prefix_data = PrefixData(prefix)
        method = getattr(prefix_data, method_name)
        packages = method()

        # Should return a list
        assert isinstance(packages, list)

        # All packages should have expected types
        for pkg in packages:
            assert pkg.package_type in expected_types, (
                f"Package {pkg.name} from {method_name}() has unexpected type {pkg.package_type}"
            )

        # Packages should be sorted alphabetically
        if packages:
            package_names = [pkg.name for pkg in packages]
            assert package_names == sorted(package_names), (
                f"Packages from {method_name}() should be sorted"
            )


@pytest.mark.parametrize(
    "environment_packages,expected_conda_count",
    [
        ([], 0),  # Empty environment
        (["small-executable"], 1),  # Single package
        (["small-executable", "sample_noarch_python"], 2),  # Multiple packages
    ],
)
def test_package_extraction_package_counts(
    tmp_env: TmpEnvFixture,
    test_recipes_channel: str,
    environment_packages: list,
    expected_conda_count: int,
):
    """Test package extraction with different environment configurations."""
    with tmp_env(*environment_packages) as prefix:
        prefix_data = PrefixData(prefix)

        conda_packages = prefix_data.get_conda_packages()

        # Check expected conda package count (allowing for dependencies)
        assert len(conda_packages) >= expected_conda_count, (
            f"Should have at least {expected_conda_count} conda packages, got {len(conda_packages)}"
        )

        # Check that expected packages are present
        conda_names = {pkg.name for pkg in conda_packages}
        for expected_package in environment_packages:
            assert expected_package in conda_names, f"Should include {expected_package}"


def test_package_methods_with_mock_data(mocker):
    """Test package extraction methods with controlled mock data."""
    # Create mock prefix data
    mock_prefix_data = mocker.Mock(spec=PrefixData)

    # Create mock records
    conda_record1 = mocker.Mock()
    conda_record1.name = "conda-package-a"
    conda_record1.package_type = None

    conda_record2 = mocker.Mock()
    conda_record2.name = "conda-package-b"
    conda_record2.package_type = PackageType.NOARCH_PYTHON

    python_record = mocker.Mock()
    python_record.name = "python-package"
    python_record.package_type = PackageType.VIRTUAL_PYTHON_WHEEL

    # Create a mock PrefixGraph that returns our test records
    mock_graph = mocker.Mock()
    mock_graph.graph = [conda_record1, conda_record2, python_record]

    # Monkeypatch the methods to use our mock data
    mock_prefix_data.get_conda_packages = PrefixData.get_conda_packages.__get__(
        mock_prefix_data
    )
    mock_prefix_data.get_python_packages = PrefixData.get_python_packages.__get__(
        mock_prefix_data
    )

    # Mock the iter_records and PrefixGraph
    mock_prefix_data.iter_records.return_value = [
        conda_record1,
        conda_record2,
        python_record,
    ]
    mocker.patch("conda.core.prefix_data.PrefixGraph", return_value=mock_graph)

    # Test the methods
    conda_packages = mock_prefix_data.get_conda_packages()
    python_packages = mock_prefix_data.get_python_packages()

    # Should have 2 conda packages and 1 Python package
    assert len(conda_packages) == 2
    assert len(python_packages) == 1

    # Should have correct names (sorted)
    assert [pkg.name for pkg in conda_packages] == [
        "conda-package-a",
        "conda-package-b",
    ]
    assert python_packages[0].name == "python-package"


def test_get_python_packages_with_pip_interoperability(
    tmp_env: TmpEnvFixture, test_recipes_channel: str
):
    """Test get_python_packages with pip interoperability enabled."""
    # Create environment with a basic package and enable pip interoperability
    with tmp_env("small-executable") as prefix:
        prefix_data = PrefixData(
            prefix, interoperability=True
        )  # Enable pip interoperability

        # Get Python packages
        python_packages = prefix_data.get_python_packages()

        # Should return a list
        assert isinstance(python_packages, list)

        # Test that the method works correctly regardless of whether there are Python packages
        # The key is testing the extraction logic and ensuring no errors occur

        # If there are Python packages, they should be sorted and have correct types
        if python_packages:
            package_names = [pkg.name for pkg in python_packages]
            assert package_names == sorted(package_names), (
                "Python packages should be sorted alphabetically"
            )

            # All should be Python packages
            for pkg in python_packages:
                assert pkg.package_type in {
                    PackageType.VIRTUAL_PYTHON_WHEEL,
                    PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE,
                    PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE,
                }, (
                    f"Package {pkg.name} should be a Python package type, got {pkg.package_type}"
                )

        # Test that both conda and Python packages are handled correctly
        conda_packages = prefix_data.get_conda_packages()

        # Should have conda packages
        assert len(conda_packages) >= 1, (
            "Should have at least the small-executable conda package"
        )
        conda_names = {pkg.name for pkg in conda_packages}
        assert "small-executable" in conda_names, "Should have small-executable package"

        # Test that interoperability doesn't break the basic functionality
        assert isinstance(conda_packages, list)
        assert isinstance(python_packages, list)


def test_method_consistency(tmp_env: TmpEnvFixture, test_recipes_channel: str):
    """Test that all methods return consistent results."""
    with tmp_env("small-executable") as prefix:
        prefix_data = PrefixData(prefix)

        # Get packages using different methods
        conda_packages = prefix_data.get_conda_packages()
        python_packages = prefix_data.get_python_packages()

        # Methods should return valid lists
        assert isinstance(conda_packages, list)
        assert isinstance(python_packages, list)

        # Should have expected content
        assert len(conda_packages) > 0, "Should have conda packages"
        conda_names = {pkg.name for pkg in conda_packages}
        assert "small-executable" in conda_names, "Should include small-executable"


@pytest.mark.parametrize("package_type", ["conda", "python"])
def test_api_consistency(
    tmp_env: TmpEnvFixture, test_recipes_channel: str, package_type: str
):
    """Test that package extraction methods return valid results."""
    with tmp_env("small-executable") as prefix:
        prefix_data = PrefixData(prefix)

        # Get packages via individual method
        if package_type == "conda":
            packages = prefix_data.get_conda_packages()
        else:  # python
            packages = prefix_data.get_python_packages()

        # Should return a list
        assert isinstance(packages, list)

        # Should be sorted
        if packages:
            package_names = [pkg.name for pkg in packages]
            assert package_names == sorted(package_names)


def test_pinned_specs_conda_meta_pinned(tmp_env: TmpEnvFixture):
    # Test pinned specs conda environment file
    specs = ("scipy ==0.14.2", "openjdk >=8")
    with tmp_env() as prefix:
        (prefix / PREFIX_PINNED_FILE).write_text("\n".join(specs) + "\n")

        prefix_data = PrefixData(prefix)
        pinned_specs = prefix_data.get_pinned_specs()
        assert pinned_specs != specs
        assert pinned_specs == tuple(MatchSpec(spec, optional=True) for spec in specs)


def test_timestamps(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
):
    start = datetime.now(tz=timezone.utc)
    with tmp_env(shallow=False) as prefix:
        pd = PrefixData(prefix)
        created = pd.created
        first_modification = pd.last_modified
        # On Linux, we allow a rounding error of a <1 second (usually ~5ms)
        assert abs(created.timestamp() - first_modification.timestamp()) < 1
        conda_cli("install", "--yes", "--prefix", prefix, "small-executable")
        second_modification = pd.last_modified
        assert created == pd.created
        assert first_modification < second_modification
        assert start < pd.created < second_modification < datetime.now(tz=timezone.utc)
