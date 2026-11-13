# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the cheatsheet data and the ``conda_cheatsheet`` Sphinx extension."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

DOCS_SOURCE = Path(__file__).resolve().parents[2] / "docs" / "source"
EXTENSIONS_DIR = DOCS_SOURCE / "_extensions"
RST_FILE = DOCS_SOURCE / "user-guide" / "cheatsheet.rst"

pytest.importorskip("sphinx")
pytest.importorskip("ruamel.yaml")
pytest.importorskip("jinja2")


@pytest.fixture
def cheatsheet(monkeypatch):
    monkeypatch.syspath_prepend(str(EXTENSIONS_DIR))
    sys.modules.pop("conda_cheatsheet", None)
    import conda_cheatsheet

    return conda_cheatsheet


@pytest.fixture
def data(cheatsheet):
    return cheatsheet.load_data()


def rst_sections() -> dict[str, str | None]:
    """Map each section title in ``cheatsheet.rst`` to its tip (if any)."""
    text = RST_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^(?P<title>[^\n]+)\n=+\n\n(?:\.\. tip::\n\n   (?P<tip>[^\n]+)\n)?",
        re.MULTILINE,
    )
    return {m["title"]: m["tip"] for m in pattern.finditer(text)}


def test_csv_files_exist_and_have_two_columns(cheatsheet, data):
    for section in data["sections"]:
        rows = cheatsheet.read_rows(cheatsheet.DATA_DIR / section["csv"])
        assert rows, section["csv"]
        assert all(description and commands for description, commands in rows)


def test_rst_titles_and_tips_match_yaml(data):
    rst = rst_sections()
    for section in data["sections"]:
        assert section["title"] in rst
        assert rst[section["title"]] == section.get("tip")


def test_rst_includes_every_csv(data):
    text = RST_FILE.read_text(encoding="utf-8")
    for section in data["sections"]:
        assert f":file: cheatsheets/{section['csv']}" in text


def test_all_placeholders_are_used(cheatsheet, data):
    commands = " ".join(
        command
        for section in data["sections"]
        for _, cmds in cheatsheet.read_rows(cheatsheet.DATA_DIR / section["csv"])
        for command in cmds
    )
    unused = [
        name
        for name in data["placeholders"]
        if not re.search(rf"\b{re.escape(name)}\b", commands)
    ]
    assert not unused


@pytest.mark.parametrize(
    "cell,expected",
    [
        ("``conda info``", ["conda info"]),
        (
            (
                "``conda install --channel CHANNELNAME PKGNAME``\n\n"
                "``conda install CHANNELNAME::PKGNAME``"
            ),
            [
                "conda install --channel CHANNELNAME PKGNAME",
                "conda install CHANNELNAME::PKGNAME",
            ],
        ),
    ],
)
def test_read_rows_splits_commands(cheatsheet, tmp_path, cell, expected):
    csv_file = tmp_path / "rows.csv"
    csv_file.write_text('description,"' + cell.replace('"', '""') + '"\n')
    assert cheatsheet.read_rows(csv_file) == [("description", expected)]


@pytest.mark.parametrize(
    "command,expected",
    [
        (
            "conda create --name ENVNAME",
            'conda create --name <span class="ph">ENVNAME</span>',
        ),
        ("conda install PKGNAME=3.1.4", None),
        ("conda update --all", "conda update --all"),
        ("conda install <b>", "conda install &lt;b&gt;"),
    ],
)
def test_highlight(cheatsheet, data, command, expected):
    html = str(cheatsheet.highlight(command, data["placeholders"]))
    if expected is None:
        assert '<span class="ph">PKGNAME</span>=<span class="ph">3.1.4</span>' in html
    else:
        assert html == expected


def test_render_pdf_has_two_pages(cheatsheet, tmp_path):
    pytest.importorskip("weasyprint")
    target = tmp_path / "cheatsheet.pdf"
    try:
        pages = cheatsheet.render_pdf(target, "0.0.0")
    except OSError as exc:
        pytest.skip(f"WeasyPrint native libraries unavailable: {exc}")
    assert target.read_bytes().startswith(b"%PDF")
    assert pages == 2


@pytest.mark.parametrize(
    "source_path,expected",
    [
        (
            "user-guide/conda-cheatsheet.pdf",
            "_downloads/843d9e0198f2a193a3484886fa28163c/conda-cheatsheet.pdf",
        ),
        (
            "user-guide/cheatsheets/conda-25.3.1.pdf",
            "_downloads/9bd19ff225f7e368e394d54d887d121a/conda-25.3.1.pdf",
        ),
        (
            "user-guide/cheatsheets/conda-24.4.0.pdf",
            "_downloads/e0795803d81d6d87b74abed339025237/conda-24.4.0.pdf",
        ),
    ],
)
def test_legacy_download_path_matches_published_urls(cheatsheet, source_path, expected):
    assert cheatsheet.legacy_download_path(source_path).as_posix() == expected


def test_archived_pdfs_are_not_linked_on_page(cheatsheet):
    # Names may only appear in the maintainers comment, never in a link.
    text = RST_FILE.read_text(encoding="utf-8")
    assert ":download:" not in text
    for name in cheatsheet.ARCHIVED_PDFS:
        assert (cheatsheet.DATA_DIR / name).is_file()


def test_copy_archived_pdfs(cheatsheet, tmp_path):
    cheatsheet.copy_archived_pdfs(tmp_path)
    for name in cheatsheet.ARCHIVED_PDFS:
        published = tmp_path / cheatsheet.legacy_download_path(
            f"{cheatsheet.ARCHIVE_DIR}/{name}"
        )
        assert published.read_bytes() == (cheatsheet.DATA_DIR / name).read_bytes()


def test_pdf_role_matches_download_markup(cheatsheet, tmp_path):
    from sphinx.application import Sphinx

    srcdir = tmp_path / "src"
    (srcdir / "sub").mkdir(parents=True)
    (srcdir / "conf.py").write_text(
        f"import sys\nsys.path.insert(0, {str(EXTENSIONS_DIR)!r})\n"
        "extensions = ['conda_cheatsheet']\n"
    )
    (srcdir / "index.rst").write_text(
        "Top\n===\n\n.. toctree::\n\n   sub/page\n\n:cheatsheet-pdf:`the sheet`\n"
    )
    (srcdir / "sub" / "page.rst").write_text(
        "Page\n====\n\n:cheatsheet-pdf:`the sheet`\n"
    )
    outdir = tmp_path / "out"
    app = Sphinx(
        str(srcdir), str(srcdir), str(outdir), str(tmp_path / "doctrees"), "html"
    )
    app.build(force_all=True)
    top = (outdir / "index.html").read_text()
    nested = (outdir / "sub" / "page.html").read_text()
    assert 'class="reference download internal" download=""' in top
    assert 'href="_static/conda-cheatsheet.pdf"' in top
    assert 'href="../_static/conda-cheatsheet.pdf"' in nested
    assert '<code class="xref download docutils literal notranslate">' in top
