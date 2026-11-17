#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Generate the developer registry of structured error hint codes.

conda attaches structured guidance to user-facing errors: a summary plus actionable
hints carrying stable ``hint_code`` identifiers. This script parses ``conda/**/*.py``,
pairs every hint declaration with the guidance summary it belongs to, and writes
``hint-code-registry.md``, the developer table of codes, messages, summaries, and
source locations.

Run it through the ``generate-hint-code-registry`` pre-commit hook, or directly:

    python docs/source/dev-guide/generate_hint_code_registry.py
"""

from __future__ import annotations

import ast
import html
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

SOURCE_ROOT = Path(__file__).resolve().parents[3] / "conda"
REGISTRY_PATH = Path(__file__).with_name("hint-code-registry.md")
GENERATOR_NAME = "docs/source/dev-guide/generate_hint_code_registry.py"

_DEFINITIONS = (
    ast.Module,
    ast.ClassDef,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
)
_RUNTIME = "(generated at runtime)"


@dataclass(frozen=True)
class HintRecord:
    """One hint code, its message and summary, and every location declaring it."""

    hint_code: str
    text: str
    summary: str | None
    locations: tuple[tuple[str, int], ...]


def _read_dict_field(node: ast.Dict, key: str) -> ast.AST | None:
    """Value of ``key`` in a dict literal, or ``None``."""
    return next(
        (
            value
            for key_node, value in zip(node.keys, node.values)
            if isinstance(key_node, ast.Constant) and key_node.value == key
        ),
        None,
    )


def _format_fstring(node: ast.JoinedStr) -> str:
    """An f-string as text with ``{expression}`` placeholders."""
    parts = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            parts.append(f"{{{ast.unparse(value.value)}}}")
    return "".join(parts)


def _read_literal(node: ast.AST) -> str:
    """A string literal or f-string, or a runtime-generated marker."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return _format_fstring(node)
    return _RUNTIME


def _parse_hint_declaration(node: ast.AST) -> tuple[str, str, int] | None:
    """The ``text``, ``hint_code``, and line if ``node`` declares a hint."""
    if isinstance(node, ast.Dict):
        text = _read_dict_field(node, "text")
        hint_code = _read_dict_field(node, "hint_code")
        if text is not None and hint_code is not None:
            return _read_literal(text), _read_literal(hint_code), hint_code.lineno
    return None


def _parse_guidance_parts(node: ast.AST) -> tuple[ast.AST, ast.AST | None] | None:
    """The ``hints`` and ``summary`` nodes if ``node`` is a guidance container."""
    if isinstance(node, ast.Dict):
        hints = _read_dict_field(node, "hints")
        if hints is not None:
            return hints, _read_dict_field(node, "summary")
    return None


def _iter_scope_nodes(scope: ast.AST) -> Iterator[ast.AST]:
    """Statements belonging to ``scope``, excluding nested definitions."""
    for child in ast.iter_child_nodes(scope):
        if isinstance(child, _DEFINITIONS):
            continue
        yield child
        yield from _iter_scope_nodes(child)


def _iter_assigned_values(
    name: str, nodes: list[ast.AST], include_appends: bool
) -> Iterator[ast.AST]:
    """Expressions assigned to ``name`` in a scope, plus appended ones."""
    for node in nodes:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            yield node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and node.value is not None
        ):
            yield node.value
        elif (
            include_appends
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == name
            and node.func.attr == "append"
            and node.args
        ):
            yield node.args[0]


def _resolve_declarations(
    node: ast.AST,
    declarations: dict[ast.AST, tuple[str, str, int]],
    nodes: list[ast.AST],
    resolving: frozenset[str] = frozenset(),
) -> set[ast.AST]:
    """Hint declarations reachable from a guidance ``hints`` expression.

    Handles a list literal and a name bound to a list that is appended to.
    """
    if node in declarations:
        return {node}
    if isinstance(node, ast.List):
        return {
            declaration
            for element in node.elts
            for declaration in _resolve_declarations(
                element, declarations, nodes, resolving
            )
        }
    if not isinstance(node, ast.Name) or node.id in resolving:
        return set()
    resolving |= {node.id}
    return {
        declaration
        for value in _iter_assigned_values(node.id, nodes, include_appends=True)
        for declaration in _resolve_declarations(value, declarations, nodes, resolving)
    }


def _collect_summary_values(
    node: ast.AST,
    nodes: list[ast.AST],
    resolving: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    """Values a guidance ``summary`` expression resolves to."""
    if isinstance(node, ast.Constant):
        return (node.value,) if isinstance(node.value, str) else ()
    if isinstance(node, ast.JoinedStr):
        return (_format_fstring(node),)
    if not isinstance(node, ast.Name) or node.id in resolving:
        return ()
    resolving |= {node.id}
    values = [
        value
        for assigned in _iter_assigned_values(node.id, nodes, include_appends=False)
        for value in _collect_summary_values(assigned, nodes, resolving)
    ]
    return tuple(dict.fromkeys(values))


def extract_hints(path: Path, display_path: str) -> Iterable[HintRecord]:
    """Every hint declared in one file, paired with its guidance summary."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for scope in ast.walk(tree):
        if not isinstance(scope, _DEFINITIONS):
            continue
        nodes = list(_iter_scope_nodes(scope))

        # Index this scope's declarations so guidance can claim them below.
        declarations = {}
        for node in nodes:
            if declaration := _parse_hint_declaration(node):
                declarations[node] = declaration

        # Pair each guidance container's hints with its summary.
        found = []
        consumed = set()
        for container in nodes:
            guidance = _parse_guidance_parts(container)
            if guidance is None:
                continue
            hints, summary_node = guidance
            if summary_node is None:
                summaries = (None,)
            elif not (summaries := _collect_summary_values(summary_node, nodes)):
                summaries = (_RUNTIME,)
            for node in _resolve_declarations(hints, declarations, nodes):
                consumed.add(node)
                found.extend((node, summary) for summary in summaries)

        # Emit declarations no guidance container references, with no summary.
        found.extend((node, None) for node in declarations if node not in consumed)

        for node, summary in found:
            text, hint_code, line = declarations[node]
            yield HintRecord(hint_code, text, summary, ((display_path, line),))


def collect_hint_records(source_root: Path = SOURCE_ROOT) -> list[HintRecord]:
    """The full registry, merging locations that declare the same hint equally."""
    grouped = {}
    for path in sorted(source_root.rglob("*.py")):
        display_path = path.relative_to(source_root.parent).as_posix()
        for record in extract_hints(path, display_path):
            key = (record.hint_code, record.text, record.summary)
            grouped.setdefault(key, set()).update(record.locations)

    records = [
        HintRecord(
            hint_code=hint_code,
            text=text,
            summary=summary,
            locations=tuple(sorted(locations)),
        )
        for (hint_code, text, summary), locations in grouped.items()
    ]
    return sorted(
        records,
        key=lambda record: (
            record.hint_code,
            record.text,
            record.summary or "",
            record.locations,
        ),
    )


def _format_cell_text(value: str) -> str:
    """Escape a value for a markdown table cell."""
    return html.escape(value, quote=False).replace("|", r"\|").replace("\n", "<br>")


def render_registry(records: Iterable[HintRecord]) -> str:
    """Render the registry records as the generated markdown page."""
    lines = [
        "# Hint code registry",
        "",
        f"<!-- This file is generated by {GENERATOR_NAME} -->",
        f"<!-- Run: python {GENERATOR_NAME} -->",
        "",
        "Structured error hints use stable `hint_code` identifiers for documentation, automation, and review. This registry is generated from hint declarations in conda's Python source; codes supplied at runtime by external plugins are not included.",
        "",
        "Values that cannot be determined statically are shown as `(generated at runtime)`.",
        "",
        "Do not edit the generated tables directly. After adding or changing a hint, run `pre-commit run generate-hint-code-registry --all-files` or the manual command above, then review and stage the generated diff. The pre-commit hook regenerates this page when relevant sources, the generator, or this page change.",
        "",
        "## Registered hint codes",
        "",
        "| Hint code | Hint message | Guidance summary | Source locations |",
        "| --- | --- | --- | --- |",
    ]
    for record in records:
        locations = "<br>".join(f"`{path}:{line}`" for path, line in record.locations)
        summary = _format_cell_text(record.summary) if record.summary else "—"
        lines.append(
            f"| `{record.hint_code}` | {_format_cell_text(record.text)} | {summary} | {locations} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    REGISTRY_PATH.write_text(
        render_registry(collect_hint_records()), encoding="utf-8", newline="\n"
    )
