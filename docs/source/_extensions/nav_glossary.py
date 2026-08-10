# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Custom Sphinx directive ``.. nav-glossary::`` for navigation index pages.

Behaves identically to ``.. glossary::`` but wraps the output ``<dl>`` in a
``<nav class="nav-glossary">`` element so that index-page navigation lists use
semantically correct HTML.  All other builders (LaTeX, text, …) treat the
wrapper as a transparent no-op, preserving existing non-HTML output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.domains.std import Glossary

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata


class nav_glossary_node(nodes.General, nodes.Element):
    """Transparent wrapper node that emits ``<nav>`` in the HTML builder."""


def _visit_nav_glossary_html(self, node: nav_glossary_node) -> None:
    self.body.append(self.starttag(node, "nav", CLASS="nav-glossary"))


def _depart_nav_glossary_html(self, node: nav_glossary_node) -> None:
    self.body.append("</nav>\n")


def _noop(self, node: nav_glossary_node) -> None:
    pass


class NavGlossary(Glossary):
    """Like ``.. glossary::`` but wraps output in a ``<nav>`` element."""

    def run(self) -> list[nodes.Node]:
        wrapper = nav_glossary_node()
        wrapper.extend(super().run())
        return [wrapper]


def setup(app: Sphinx) -> ExtensionMetadata:
    app.add_node(
        nav_glossary_node,
        html=(_visit_nav_glossary_html, _depart_nav_glossary_html),
        latex=(_noop, _noop),
        text=(_noop, _noop),
        man=(_noop, _noop),
        texinfo=(_noop, _noop),
    )
    app.add_directive("nav-glossary", NavGlossary)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
