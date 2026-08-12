# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Custom Sphinx directive ``nav-glossary`` for navigation index pages.

Behaves like ``glossary`` but wraps the output ``<dl>`` in a
``<nav class="nav-glossary">`` element so that index-page navigation lists use
semantically correct HTML.  All other builders (LaTeX, text, …) treat the
wrapper as a transparent no-op, preserving existing non-HTML output.

Usage in reStructuredText::

    .. nav-glossary::

        :doc:`Title <target>`
            Description with ``literals``.

Usage in MyST Markdown (body must still use RST roles and definition-list
indentation)::

    ```{nav-glossary}
    :doc:`Title <target>`
        Description with ``literals``.
    ```

``option_spec`` is intentionally empty.  MyST only scans for a ``:option:``
block when ``option_spec`` is truthy; an empty spec lets ``:doc:`` roles start
the body without a leading blank line.  Nav lists are authored in order, so
glossary ``:sorted:`` is not supported.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes
from docutils.parsers.rst import Parser as RSTParser
from docutils.utils import new_document
from sphinx.domains.std import Glossary

if TYPE_CHECKING:
    from typing import Any, ClassVar

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
    """Like ``glossary`` but wraps output in a ``<nav>`` element.

    When invoked from MyST, ``self.state`` is a MockState whose
    ``inline_text`` / ``nested_parse`` treat content as Markdown.  Re-parse the
    body through a real RST ``glossary`` so ``:doc:`` roles and ``literals``
    match ``.. nav-glossary::`` in ``.rst`` files.
    """

    # See module docstring: empty so MyST does not treat ``:doc:`` as options.
    option_spec: ClassVar[dict[str, Any]] = {}

    def run(self) -> list[nodes.Node]:
        wrapper = nav_glossary_node()
        if type(self.state).__module__ == "myst_parser.mocking":
            wrapper.extend(self._glossary_nodes_via_rst())
        else:
            wrapper.extend(super().run())
        return [wrapper]

    def _glossary_nodes_via_rst(self) -> list[nodes.Node]:
        """Parse this directive's body as RST ``.. glossary::``."""
        lines = [".. glossary::", ""]
        for line in self.content:
            lines.append(f"    {line}" if line else "")
        text = "\n".join(lines) + "\n"

        document = self.state.document
        newdoc = new_document(document["source"], document.settings)
        newdoc.reporter = document.reporter
        RSTParser().parse(text, newdoc)

        for node in newdoc.children:
            names = node.get("names") if isinstance(node, nodes.Element) else None
            if names:
                document.note_explicit_target(node, node)
        return list(newdoc.children)


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
        "version": "0.2",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
