# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from logging import getLogger

from .match_spec import MatchSpec
from ..common.url import quote as url_quote

log = getLogger(__name__)


class SimpleDag(object):
    # This is in conda.models and not conda.common because it isn't general and assumes
    #   knowledge of record and match_spec structure.
    # Not immutable.  Also optimizing for convenience, not performance.
    #   For < ~1,000 packages, performance shouldn't be a problem.
    # Nodes don't yet have a 'constrained_by' method of optional constrained dependencies.

    def __init__(self, records, specs):
        self.nodes = []
        self.spec_matches = defaultdict(list)

        for record in records:
            Node(self, record)

        for spec in specs:
            self.add_spec(spec)

    def add_spec(self, spec):
        for node in self.nodes:
            if spec.match(node.record):
                node.specs.append(spec)
                self.spec_matches[spec].append(node)

    def remove_spec(self, spec):
        removed = []
        for node in iter(self.nodes):
            if spec.match(node.record):
                removed.extend(self.remove_node_and_children(node))
        return removed

    def remove_node_and_children(self, node):
        for child in node.required_children:
            for record in self.remove_node_and_children(child):
                yield record
        yield self.remove(node)

    def dot_repr(self, title=None):
        # graphviz DOT graph description language

        builder = ['digraph g {']
        if title:
            builder.append('  labelloc="t";')
            builder.append('  label="%s";' % title)
        builder.append('  size="10.5,8";')
        builder.append('  rankdir=BT;')
        for node in self.nodes:
            label = "%s %s" % (node.record.name, node.record.version)
            if node.specs:
                # TODO: combine?
                spec = node.specs[0]
                label += "\\n%s" % ("?%s" if spec.optional else "%s") % spec
            if node.is_orphan:
                shape = "box"
            elif node.is_root:
                shape = "invhouse"
            elif node.is_leaf:
                shape = "house"
            else:
                shape = "ellipse"
            builder.append('  "%s" [label="%s", shape=%s];' % (node.record.name, label, shape))
            for child in node.required_children:
                builder.append('    "%s" -> "%s";' % (child.record.name, node.record.name))
            for child in node.optional_children:
                builder.append('    "%s -> "%s" [color=lightgray];' % (child.record.name, node.record.name))
        builder.append('}')
        return '\n'.join(builder)

    def open_url(self):
        import webbrowser
        url = "https://condaviz.glitch.me/%s" % url_quote(self.dot_repr())
        print(url)
        browser = webbrowser.get("safari")
        browser.open_new_tab(url)

    @property
    def orphans(self):
        return (node for node in self.nodes if node.is_orphan)

    @property
    def roots(self):
        return (node for node in self.nodes if node.is_root)

    @property
    def leaves(self):
        return (node for node in self.nodes if node.is_leaf)

    @property
    def records(self):
        return (node.record for node in self.nodes)

    def prune(self):
        for orphan in self.orphans:
            if not orphan.specs:
                self.nodes.remove(orphan)

        def remove_leaves_one_pass():
            for leaf in self.leaves:
                if not leaf.specs or leaf.specs[0].optional:
                    self.remove(leaf)

        num_nodes_pre = len(self.nodes)
        remove_leaves_one_pass()
        num_nodes_post = len(self.nodes)
        while num_nodes_pre != num_nodes_post:
            num_nodes_pre = num_nodes_post
            remove_leaves_one_pass()
            num_nodes_post = len(self.nodes)

    def remove(self, node):
        for parent in node.required_parents:
            parent.required_children.remove(node)
        for parent in node.optional_parents:
            parent.optional_children.remove(node)
        for child in node.required_children:
            child.required_parents.remove(node)
        for child in node.optional_children:
            child.optional_parents.remove(node)
        for spec in node.specs:
            self.spec_matches[spec].remove(node)
        self.nodes.remove(node)
        return node.record










class Node(object):

    def __init__(self, dag, record):
        self.record = record
        self._constrains = tuple(MatchSpec(s).name for s in record.constrains)
        self._depends = tuple(MatchSpec(s).name for s in record.depends)

        self.optional_parents = []
        self.optional_children = []
        self.required_parents = []
        self.required_children = []
        self.specs = []

        for old_node in dag.nodes:
            if self.constrained_by(old_node):
                self.optional_parents.append(old_node)
                old_node.optional_children.append(self)
            elif self.depends_on(old_node):
                self.required_parents.append(old_node)
                old_node.required_children.append(self)
            elif old_node.constrained_by(self):
                old_node.optional_parents.append(self)
                self.optional_children.append(old_node)
            elif old_node.depends_on(self):
                old_node.required_parents.append(self)
                self.required_children.append(old_node)

        for spec in dag.spec_matches:
            if spec.match(record):
                self.specs.append(spec)
                dag.spec_matches[spec].append(self)

        dag.nodes.append(self)

    def constrained_by(self, other):
        return other.record.name in self._constrains

    def depends_on(self, other):
        return other.record.name in self._depends

    def all_descendants(self):
        def _all_descendants():
            for child in self.required_children:
                for gchild in child.required_children:
                    yield gchild
                yield child
        import pdb; pdb.set_trace()
        return tuple(_all_descendants())


    has_children = property(lambda self: self.required_children or self.optional_children)
    has_parents = property(lambda self: self.required_parents or self.optional_parents)
    is_root = property(lambda self: self.has_children and not self.has_parents)
    is_leaf = property(lambda self: self.has_parents and not self.has_children)
    is_orphan = property(lambda self: not self.has_parents and not self.has_children)

