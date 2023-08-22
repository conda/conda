# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda_env.env import Environment
from conda_env.specs.remote import RemoteSpec


def test_can_handle_no_uri():
    spec = RemoteSpec()
    assert not spec.uri
    assert not spec.can_handle()
    assert spec.msg == "Can't process without a uri"


def test_invalid_uri():
    spec = RemoteSpec("not-a-uri")
    assert not spec.can_handle()
    assert (
        spec.msg
        == "You need to install the package that provides the FSSpec None protocol."
    )


def test_invalid_protocol():
    spec = RemoteSpec("___foo://path")
    assert not spec.can_handle()
    assert (
        spec.msg
        == "You need to install the package that provides the FSSpec ___foo protocol."
    )


def test_download_environment():
    uri = "github://conda:conda@a1c4cf4/tests/conda_env/support/example/environment_pinned.yml"

    spec = RemoteSpec(uri)
    assert spec.can_handle()
    assert isinstance(spec.environment, Environment)
    assert "flask==2.0.2" in spec.environment.dependencies["conda"]
