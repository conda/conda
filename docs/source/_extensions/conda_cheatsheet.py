# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Sphinx extension that generates the conda cheatsheet PDF at build time.

The PDF is rendered with WeasyPrint from the same CSV files that feed the
tables on ``user-guide/cheatsheet.rst``, plus ``cheatsheets/cheatsheet.yml``
for section order, tips and footer links.  It is written to
``<outdir>/_static/conda-cheatsheet.pdf`` after the HTML build.

The PDF used to be a committed file linked with ``:download:`` from
``user-guide/cheatsheet.rst``, which Sphinx publishes at
``_downloads/<md5 of the source path>/conda-cheatsheet.pdf``.  That URL is
public and long-lived, so a copy is also written there to keep old links
working. The archived PDFs in ``user-guide/cheatsheets/`` are no longer linked
from the page, so they are copied to their old ``_downloads`` URLs too.

The ``:cheatsheet-pdf:`` role links the generated PDF using the same markup
as ``:download:`` (including the theme's download icon), but without
requiring the file to exist when the page is read.

If WeasyPrint (or its native libraries) is unavailable, a warning is emitted
and the rest of the build continues.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import posixpath
import re
import shutil
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING

from docutils import nodes
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from ruamel.yaml import YAML
from sphinx.util import logging

if TYPE_CHECKING:
    from typing import Any

    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

log = logging.getLogger(__name__)

PDF_NAME = "conda-cheatsheet.pdf"
PDF_STATIC_PATH = Path("_static") / PDF_NAME

# Sphinx publishes ``:download:`` files at ``_downloads/<md5 of the source path
# relative to the docs source dir>/<file name>``. These paths are public, so
# the files below are still copied there even though no page links them.
ARCHIVE_DIR = "user-guide/cheatsheets"
ARCHIVED_PDFS = (
    "conda-25.3.1.pdf",
    "conda-24.4.0.pdf",
    "conda-4.14.pdf",
    "conda-4.12.pdf",
    "conda-4.6.pdf",
)


def legacy_download_path(source_path: str) -> Path:
    """Return where Sphinx publishes a ``:download:`` file, relative to outdir."""
    digest = hashlib.md5(source_path.encode(), usedforsecurity=False).hexdigest()
    return Path("_downloads") / digest / Path(source_path).name


# The current cheatsheet used to be the symlink ``user-guide/conda-cheatsheet.pdf``.
LEGACY_PDF_PATH = legacy_download_path(f"user-guide/{PDF_NAME}")

_HERE = Path(__file__).resolve().parent
SOURCE_DIR = _HERE.parent
DATA_DIR = SOURCE_DIR / "user-guide" / "cheatsheets"
DATA_FILE = DATA_DIR / "cheatsheet.yml"
ASSETS_DIR = SOURCE_DIR / "_static" / "cheatsheet"
# WeasyPrint ignores the SVG masks used by ``_static/img/conda_logo.svg``, so
# the PDF embeds a PNG render of it instead. To regenerate it (needs resvg-py)::
#
#     resvg_py.svg_to_bytes(svg_path="_static/img/conda_logo.svg", width=360)
LOGO_FILE = ASSETS_DIR / "conda_logo.png"

BULB_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
    '<path d="M8 0a5 5 0 0 0-3 9c.6.5 1 1.1 1 2h4c0-.9.4-1.5 1-2a5 5 0 0 0-3-9z"/>'
    '<path d="M6 12.5h4v1.2a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1z"/>'
    "</svg>"
)

_VERSION_RE = r"\d+(?:\.\d+)+"


def load_data(data_file: Path = DATA_FILE) -> dict[str, Any]:
    """Load the cheatsheet definition."""
    with data_file.open(encoding="utf-8") as fh:
        return YAML(typ="safe").load(fh)


def clean_cell(cell: str) -> str:
    """Strip RST double-backtick literal markup from a CSV cell."""
    return cell.strip().replace("``", "")


def read_rows(csv_file: Path) -> list[tuple[str, list[str]]]:
    """Read a two-column CSV into ``(description, [commands])`` tuples.

    A cell holding several commands separates them with a blank line.
    """
    rows = []
    with csv_file.open(encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh):
            if not row:
                continue
            description, command = row[0].strip(), clean_cell(row[1])
            commands = [
                " ".join(chunk.split())
                for chunk in re.split(r"\n\s*\n", command)
                if chunk.strip()
            ]
            rows.append((description, commands))
    return rows


def highlight(command: str, placeholders: list[str]) -> Markup:
    """Escape ``command`` and wrap placeholders and version numbers in spans."""
    names = "|".join(sorted(map(re.escape, placeholders), key=len, reverse=True))
    pattern = re.compile(rf"\b(?:{names})\b|(?<![\w.]){_VERSION_RE}(?![\w.])")
    out, last = [], 0
    for match in pattern.finditer(command):
        out.append(escape(command[last : match.start()]))
        out.append(f'<span class="ph">{escape(match.group())}</span>')
        last = match.end()
    out.append(escape(command[last:]))
    return Markup("".join(out))


def build_context(data: dict[str, Any], version: str) -> dict[str, Any]:
    """Assemble the template context from the YAML and CSV data."""
    placeholders = data.get("placeholders", [])
    sections = []
    for section in data["sections"]:
        rows = [
            {
                "description": description,
                "commands": [highlight(c, placeholders) for c in commands],
            }
            for description, commands in read_rows(DATA_DIR / section["csv"])
        ]
        sections.append({**section, "rows": rows})
    logo_uri = ""
    if LOGO_FILE.exists():
        encoded = base64.b64encode(LOGO_FILE.read_bytes()).decode("ascii")
        logo_uri = f"data:image/png;base64,{encoded}"
    return {
        "title": data["title"],
        "version": version,
        "sections": sections,
        "footer": data.get("footer", []),
        "logo_uri": logo_uri,
        "bulb_svg": Markup(BULB_SVG),
    }


def render_html(data: dict[str, Any], version: str) -> str:
    """Render the cheatsheet HTML document."""
    env = Environment(loader=FileSystemLoader(ASSETS_DIR), autoescape=True)
    template = env.get_template("template.html.j2")
    return template.render(**build_context(data, version))


def render_pdf(target: Path, version: str, data_file: Path = DATA_FILE) -> int:
    """Render the cheatsheet to ``target`` and return its page count.

    Raises:
        ImportError, OSError: If WeasyPrint or its native libraries are missing.
    """
    from weasyprint import CSS, HTML
    from weasyprint.text.fonts import FontConfiguration

    html = render_html(load_data(data_file), version)
    font_config = FontConfiguration()
    document = HTML(string=html, base_url=str(ASSETS_DIR) + "/").render(
        stylesheets=[
            CSS(filename=str(ASSETS_DIR / "cheatsheet.css"), font_config=font_config)
        ],
        font_config=font_config,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    document.write_pdf(str(target))
    return len(document.pages)


class cheatsheet_pdf_node(nodes.reference):
    """Link to the generated PDF, rendered like a ``download_reference``.

    Sphinx's own ``download_reference`` is tied to source files that exist when
    the page is read, which is not true for a PDF generated after the build.
    """


def _visit_cheatsheet_pdf_html(self: Any, node: cheatsheet_pdf_node) -> None:
    # Same attributes as Sphinx's ``visit_download_reference`` for a file, so
    # the theme's ``a.reference.download`` rule adds its download icon.
    atts = {
        "class": "reference download internal",
        "download": "",
        "href": node["refuri"],
    }
    self.body.append(self.starttag(node, "a", "", **atts))


def _depart_cheatsheet_pdf_html(self: Any, node: cheatsheet_pdf_node) -> None:
    self.body.append("</a>")


def _visit_cheatsheet_pdf_plain(self: Any, node: cheatsheet_pdf_node) -> None:
    pass


def _depart_cheatsheet_pdf_plain(self: Any, node: cheatsheet_pdf_node) -> None:
    pass


def cheatsheet_pdf_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Any,
    options: dict[str, Any] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    """Link the generated PDF like ``:download:``, e.g. ``:cheatsheet-pdf:`text```."""
    env = inliner.document.settings.env
    depth = env.docname.count("/")
    uri = posixpath.join(*[".."] * depth, PDF_STATIC_PATH.as_posix())
    literal = nodes.literal(rawtext, text, classes=["xref", "download"])
    ref = cheatsheet_pdf_node(rawtext, "", literal, refuri=uri)
    return [ref], []


def copy_archived_pdfs(outdir: Path) -> None:
    """Publish the archived PDFs at their historical ``_downloads`` URLs."""
    for name in ARCHIVED_PDFS:
        source = DATA_DIR / name
        if not source.is_file():
            log.warning("Archived cheatsheet PDF is missing: %s", source)
            continue
        target = outdir / legacy_download_path(f"{ARCHIVE_DIR}/{name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def generate_pdf(app: Sphinx, exception: Exception | None) -> None:
    """``build-finished`` hook: write the PDF for the ``html`` builder only."""
    if exception is not None or app.builder.name != "html":
        return
    outdir = Path(app.outdir)
    copy_archived_pdfs(outdir)
    target = outdir / PDF_STATIC_PATH
    try:
        render_pdf(target, str(app.config.release))
    except (ImportError, OSError) as exc:
        log.warning(
            "Skipping cheatsheet PDF, WeasyPrint is unavailable: %s",
            exc,
            type="conda_cheatsheet",
        )
        return
    except Exception as exc:
        log.warning(
            "Could not generate the cheatsheet PDF: %s",
            exc,
            type="conda_cheatsheet",
        )
        return
    legacy = outdir / LEGACY_PDF_PATH
    legacy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(target, legacy)
    log.info("Generated cheatsheet PDF: %s", target)


def setup(app: Sphinx) -> ExtensionMetadata:
    app.add_node(
        cheatsheet_pdf_node,
        html=(_visit_cheatsheet_pdf_html, _depart_cheatsheet_pdf_html),
        latex=(_visit_cheatsheet_pdf_plain, _depart_cheatsheet_pdf_plain),
        text=(_visit_cheatsheet_pdf_plain, _depart_cheatsheet_pdf_plain),
        man=(_visit_cheatsheet_pdf_plain, _depart_cheatsheet_pdf_plain),
        texinfo=(_visit_cheatsheet_pdf_plain, _depart_cheatsheet_pdf_plain),
    )
    app.add_role("cheatsheet-pdf", cheatsheet_pdf_role)
    app.connect("build-finished", generate_pdf)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
