from os.path import dirname, isdir, isfile, join

import json
import mock
import os
import pytest

from conda import CONDA_PACKAGE_ROOT
from conda.base.context import context
from conda.cli.python_api import run_command
from conda.core.subdir_data import (
    SubdirData,
    fetch_channel_signing_data,
    verify_trust_delegation,
)
from conda.gateways.connection import ConnectionError
from conda.models.channel import Channel

from tests.test_create import (
    make_temp_env,
    reload_config,
    run_command as run_command2,
    Commands,
    package_is_installed,
)


def test_root_chain():
    "mock root chaining tests (false roots, see conda-content-trust tests in test_root.py; just overwrite the built-in constant during the test)"


@pytest.mark.integration
def test_subdir_data_fetch_channel_signing_data():
    with make_temp_env("conda-content-trust") as prefix:

        with open(join(prefix, "condarc"), "a") as fh:
            fh.write("extra_safety_checks: true\n")
        reload_config(prefix)
        assert context.extra_safety_checks

        with mock.patch(
            "conda.core.subdir_data.fetch_channel_signing_data",
            wraps=fetch_channel_signing_data,
            return_value="sekrit",
        ) as fetcher:
            subdir_data = SubdirData(Channel("pkgs/main/linux-64"))
            subdir_data.load()
            assert fetcher.call_count == 2
            SubdirData.clear_cached_local_channel_data()


@pytest.mark.integration
def test_verification_with_key_mgr():
    "test verification with key_mgr in etc/conda"

    with make_temp_env("conda-content-trust") as prefix:
        # add a manual key_mgr.json because we can
        if not isdir(context.av_data_dir):
            os.makedirs(context.av_data_dir)
        key_mgr_json = join(context.av_data_dir, "key_mgr.json")

        with open(join(prefix, "condarc"), "a") as fh:
            fh.write("extra_safety_checks: true\n")
        reload_config(prefix)
        with open(key_mgr_json, "w") as key_mgr:
            key_mgr.write(json.dumps("{}"))

        # preventing fetching signing data from server
        mock.patch(
            "conda.core.subdir_data.fetch_channel_signing_data",
            side_effect=ConnectionError,
        )

        with mock.patch(
            "conda.core.subdir_data.verify_trust_delegation",
            wraps=verify_trust_delegation,
        ) as verifier:

            stdout, stderr, _ = run_command(
                Commands.INSTALL,
                prefix,
                "flask=0.12",
            )
            assert package_is_installed(prefix, "flask=0.12.2")
            assert verifier.called


def test_verification_without_key_mgr():
    "test verification without key_mgr in etc/conda"


def test_verification_with_root():
    "test verification with root in etc/conda"


def test_verification_without_root():
    "test verification without root in etc/conda"


def test_invalid_metadata():
    "test with invalid format metadata in etc/conda"
    pass


@pytest.mark.integration
def test_imports_with_conda_content_trust():
    "imports work with conda-content-trust installed"
    # conda-content-trust is installed by default
    from conda.core.subdir_data import cct

    assert cct is not None


@pytest.mark.integration
def test_imports_without_conda_content_trust():
    "imports work without conda-content-trust installed"
    conda_dev_srcdir = dirname(CONDA_PACKAGE_ROOT)

    # TODO: check why ruamel_yaml is needed here to prevent error in dev?
    with make_temp_env("ruamel_yaml") as prefix:
        assert not package_is_installed(prefix, "conda-content-trust")
        stdout, _, _ = run_command2(
            Commands.RUN,
            prefix,
            "--cwd",
            conda_dev_srcdir,
            "python",
            "-c",
            "import sys; "
            "from conda.core.subdir_data import cct; "
            "sys.stdout.write('conda-content-trust missing' if cct is None else cct)",
            dev=True,
        )
        assert "conda-content-trust missing" in stdout


def test_repo_data_valid_signatures():
    "test pulling small repodata sample and verifying the values, with mock data and invalid  (Possibly see test_authentication.py?)"


def test_repo_data_invalid_signatures():
    "test pulling small repodata sample and verifying the values, with mock data and invalid signatures.  (Possibly see test_authentication.py?)"


def test_mismatching_artifact():
    "test feeding an artifact that doesn’t match trusted hash"
