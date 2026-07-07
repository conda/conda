# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from conda.env.installers.pip import install


def test_pip_installer_resolves_multiple_requirement_sources_once(tmp_path, mocker):
    first_workdir = tmp_path / "first"
    second_workdir = tmp_path / "second"
    first_workdir.mkdir()
    second_workdir.mkdir()
    first_pkg = first_workdir / "pkg"
    second_requirements = second_workdir / "requirements.txt"
    second_requirements.touch()
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
