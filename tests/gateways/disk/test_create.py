# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import ast
import json
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path

import pytest

from conda._private import pyc_compiler
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


def test_compile_multiple_pyc_uses_direct_pair_compiler(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    prefix = tmp_path / "prefix"
    source = prefix / "lib/python3.12/site-packages/demo.py"
    target = prefix / "lib/python3.12/site-packages/__pycache__/demo.cpython-312.pyc"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1")
    calls = []

    def fake_any_subprocess(command, command_prefix):
        pairs = json.loads(Path(command[3]).read_text())
        calls.append((command, command_prefix, pairs))
        assert command[1] == "-Wi"
        assert Path(command[2]).resolve() == Path(pyc_compiler.__file__).resolve()
        assert "-c" not in command
        assert all("\n" not in arg for arg in command)
        assert "compileall" not in command
        assert pairs == [
            [
                str(Path("lib/python3.12/site-packages/demo.py")),
                str(
                    Path(
                        "lib/python3.12/site-packages/__pycache__/demo.cpython-312.pyc"
                    )
                ),
            ]
        ]
        target.parent.mkdir(parents=True)
        target.write_bytes(b"pyc")
        return "", "", 0

    monkeypatch.setattr(gateway_subprocess, "any_subprocess", fake_any_subprocess)

    created = create.compile_multiple_pyc(
        "/prefix/bin/python",
        [str(source)],
        [str(target)],
        str(prefix),
        "3.12",
    )

    assert created == [str(target)]
    assert calls == [
        (
            [
                "/prefix/bin/python",
                "-Wi",
                calls[0][0][2],
                calls[0][0][3],
            ],
            str(prefix),
            [
                [
                    str(Path("lib/python3.12/site-packages/demo.py")),
                    str(
                        Path(
                            "lib/python3.12/site-packages/__pycache__/"
                            "demo.cpython-312.pyc"
                        )
                    ),
                ]
            ],
        )
    ]


def test_private_pyc_compiler_compiles_pairs(tmp_path):
    prefix = tmp_path / "prefix"
    source = prefix / "lib/python3.12/site-packages/demo.py"
    target = prefix / "lib/python3.12/site-packages/__pycache__/demo.cpython-312.pyc"
    pairs_file = tmp_path / "pairs.json"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1")
    pairs_file.write_text(
        json.dumps(
            [
                [
                    str(source.relative_to(prefix)),
                    str(target.relative_to(prefix)),
                ]
            ]
        )
    )

    result = subprocess.run(
        [sys.executable, str(Path(pyc_compiler.__file__).resolve()), str(pairs_file)],
        cwd=prefix,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert target.is_file()


def test_private_pyc_compiler_does_not_import_conda():
    source = Path(pyc_compiler.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.partition(".")[0])

    assert "conda" not in imports
