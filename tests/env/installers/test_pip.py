# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from conda.env.installers.pip import install


@pytest.fixture
def captured_pip_subprocess(mocker):
    captured = {}

    def pip_subprocess(pip_args, prefix, cwd):
        requirements = Path(pip_args[3])

        captured["pip_args"] = pip_args
        captured["prefix"] = prefix
        captured["cwd"] = cwd
        captured["requirements_text"] = requirements.read_text()

        return "Successfully installed aiobotocore boto3", ""

    mock_pip_subprocess = mocker.patch(
        "conda.env.installers.pip.pip_subprocess",
        side_effect=pip_subprocess,
    )
    return mock_pip_subprocess, captured


def test_pip_installer_resolves_multiple_requirement_sources_once(
    tmp_path,
    captured_pip_subprocess,
):
    first_workdir = tmp_path / "first"
    second_workdir = tmp_path / "second"
    first_workdir.mkdir()
    second_workdir.mkdir()
    first_pkg = first_workdir / "pkg"
    second_requirements = second_workdir / "requirements.txt"
    second_requirements.touch()
    mock_pip_subprocess, captured = captured_pip_subprocess

    result = install(
        "/prefix",
        ["boto3>1.43.38", "aiobotocore==3.6.0"],
        Namespace(file=[]),
        requirements_sources=[
            (["boto3>1.43.38", "-e ./pkg"], str(first_workdir)),
            (["aiobotocore==3.6.0", "-r requirements.txt"], str(second_workdir)),
        ],
    )

    mock_pip_subprocess.assert_called_once()
    assert captured["pip_args"][:3] == ["install", "-U", "-r"]
    assert captured["pip_args"][4] == "--exists-action=b"
    assert captured["prefix"] == "/prefix"
    assert captured["cwd"] is None
    assert captured["requirements_text"] == (
        f"boto3>1.43.38\n-e {first_pkg}\naiobotocore==3.6.0\n-r {second_requirements}"
    )
    assert result == ["aiobotocore", "boto3"]


@pytest.mark.parametrize(
    ("spec_template", "expected_template"),
    [
        ("--editable=./pkg", "--editable={workdir}/pkg"),
        ("--requirement=requirements.txt", "--requirement={workdir}/requirements.txt"),
        ("--constraint constraints.txt", "--constraint {workdir}/constraints.txt"),
        ("./pkg", "{workdir}/pkg"),
        (
            "-e git+https://example.com/pkg.git#egg=pkg",
            "-e git+https://example.com/pkg.git#egg=pkg",
        ),
        ("--constraint={absolute}", "--constraint={absolute}"),
    ],
)
def test_pip_installer_normalizes_relative_source_paths(
    spec_template,
    expected_template,
    tmp_path,
    captured_pip_subprocess,
):
    workdir = tmp_path / "source"
    other_workdir = tmp_path / "other"
    workdir.mkdir()
    other_workdir.mkdir()
    format_args = {
        "absolute": tmp_path / "constraints.txt",
        "workdir": workdir,
    }
    spec = spec_template.format(**format_args)
    expected = expected_template.format(**format_args)
    _, captured = captured_pip_subprocess

    install(
        "/prefix",
        [spec, "requests"],
        Namespace(file=[]),
        requirements_sources=[
            ([spec], str(workdir)),
            (["requests"], str(other_workdir)),
        ],
    )

    assert captured["cwd"] is None
    assert captured["requirements_text"] == f"{expected}\nrequests"


def test_pip_installer_uses_common_source_workdir(
    tmp_path,
    captured_pip_subprocess,
):
    workdir = tmp_path / "source"
    workdir.mkdir()
    _, captured = captured_pip_subprocess

    install(
        "/prefix",
        ["-e ./pkg", "-r requirements.txt"],
        Namespace(file=[]),
        requirements_sources=[
            (["-e ./pkg"], str(workdir)),
            (["-r requirements.txt"], str(workdir)),
        ],
    )

    assert captured["cwd"] == str(workdir)
    assert captured["requirements_text"] == "-e ./pkg\n-r requirements.txt"
