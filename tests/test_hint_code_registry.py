# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from textwrap import dedent

MODULE_PATH = (
    Path(__file__).parents[1]
    / "docs"
    / "source"
    / "dev-guide"
    / "generate_hint_code_registry.py"
)


def _load_generator():
    spec = importlib.util.spec_from_file_location("hint_code_registry", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


registry = _load_generator()


def _write_source(tmp_path: Path, source: str) -> Path:
    source_root = tmp_path / "conda"
    source_root.mkdir()
    (source_root / "example.py").write_text(dedent(source).lstrip(), encoding="utf-8")
    return source_root


def test_collects_inline_hints(tmp_path: Path):
    source_root = _write_source(
        tmp_path,
        """
        def fail():
            raise CondaError(
                guidance={
                    "summary": "The operation could not finish.",
                    "hints": [
                        {
                            "text": "Check the configuration:\\n      conda info",
                            "hint_code": "check_configuration",
                        }
                    ],
                },
            )
        """,
    )

    records = registry.collect_hint_records(source_root)

    assert len(records) == 1
    record = records[0]
    assert record.hint_code == "check_configuration"
    assert record.text == "Check the configuration:\n      conda info"
    assert record.summary == "The operation could not finish."
    assert record.locations == (("conda/example.py", 8),)


def test_collects_indirect_hints_and_summary_variants(tmp_path: Path):
    source_root = _write_source(
        tmp_path,
        """
        def build_guidance(name, file=None):
            hints = []
            hints.append(
                {
                    "text": "Request an available installer.",
                    "hint_code": "check_available_installer",
                }
            )
            if file:
                summary = f"Unable to install {name} from {file}."
            else:
                summary = f"Unable to install {name}."
            return {"summary": summary, "hints": hints}
        """,
    )

    records = registry.collect_hint_records(source_root)

    assert len(records) == 2
    assert {record.summary for record in records} == {
        "Unable to install {name} from {file}.",
        "Unable to install {name}.",
    }
    assert all(record.text == "Request an available installer." for record in records)
    assert all(len(record.locations) == 1 for record in records)


def test_renders_markdown_with_escaping():
    record = registry.HintRecord(
        hint_code="check_configuration",
        text="Inspect <configuration> | retry:\n      conda info",
        summary="The operation failed.",
        locations=(("conda/example.py", 3),),
    )

    rendered = registry.render_registry([record])

    assert "Inspect &lt;configuration&gt; \\| retry:<br>      conda info" in rendered
    assert "`conda/example.py:3`" in rendered
    assert rendered.endswith("\n")
