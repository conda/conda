# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext

import pytest

from conda.base.context import context
from conda.gateways import subprocess as gateway_subprocess
from conda.gateways.disk import create


@pytest.mark.parametrize(
    "function,raises",
    [
        ("create_application_entry_point", TypeError),
        ("ProgressFileWrapper", TypeError),
        ("create_fake_executable_softlink", TypeError),
        ("extract_tarball", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(create, function)()


@pytest.mark.parametrize(
    ("default_threads", "expected_processes"),
    [(0, "0"), (2, "2")],
)
def test_compile_multiple_pyc_uses_default_threads(
    monkeypatch, tmp_path, default_threads, expected_processes
):
    prefix = tmp_path / "prefix"
    source = prefix / "lib/python3.12/site-packages/demo.py"
    target = prefix / "lib/python3.12/site-packages/__pycache__/demo.cpython-312.pyc"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1")
    commands = []

    def fake_any_subprocess(command, command_prefix):
        commands.append(command)
        target.parent.mkdir(parents=True)
        target.write_bytes(b"pyc")
        return "", "", 0

    monkeypatch.setattr(gateway_subprocess, "any_subprocess", fake_any_subprocess)

    with context._override("_default_threads", default_threads):
        created = create.compile_multiple_pyc(
            "/prefix/bin/python",
            [str(source)],
            [str(target)],
            str(prefix),
            "3.12",
        )

    assert created == [str(target)]
    assert commands[0][-2:] == ["-j", expected_processes]
