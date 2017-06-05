# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from logging import getLogger

from .match_spec import MatchSpec

log = getLogger(__name__)


class SimpleDag(object):
    # This is in conda.models and not conda.common because it isn't general and assumes
    #   knowledge of record and match_spec structure.
    # Not immutable.  Also optimizing for convenience, not performance.
    #   For < ~1,000 packages, performance shouldn't be a problem.
    # Nodes don't yet have a 'constrained_by' method of optional constrained dependencies.

    def __init__(self, records, specs):
        self.records = list(records)
        self.specs = list(specs)

        self.nodes = nodes = []
        self.roots = roots = []
        self.leaves = leaves = []
        self.orphans = orphans = []
        self.spec_matches = spec_matches = defaultdict(list)

        for record in records:
            new_node = Node(record)
            nodes.append(new_node)
            for old_node in nodes:
                if new_node.constrained_by(old_node):
                    new_node.optional_parents.append(old_node)
                    old_node.optional_children.append(new_node)
                elif new_node.depends_on(old_node):
                    new_node.required_parents.append(old_node)
                    old_node.required_children.append(new_node)

        for node in nodes:
            for spec in specs:
                if spec.match(node.record):
                    node.specs.append(spec)
                    spec_matches[spec].append(node)
            if node.is_orphan:
                orphans.append(node)
            elif node.is_root:
                roots.append(node)
            elif node.is_leaf:
                leaves.append(node)

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
                label += "\\n%s" % node.specs[0]
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
        from ..common.url import quote
        import webbrowser
        url = "https://condaviz.glitch.me/%s" % quote(self.dot_repr())
        print(url)
        browser = webbrowser.get("safari")
        browser.open_new_tab(url)

    def prune(self):
        removed_orphans = []
        for orphan in self.orphans:
            if not orphan.specs:
                self.nodes.remove(orphan)
                self.records.remove(orphan.record)
                removed_orphans.append(orphan)
        for orphan in removed_orphans:
            self.orphans.remove(orphan)

        def remove_leaves_one_pass():
            removed_leaves = []
            for leaf in self.leaves:
                if not leaf.specs:
                    self.nodes.remove(leaf)
                    self.records.remove(leaf.record)
                    for parent in leaf.required_parents:
                        parent.required_children.remove(leaf)
                        if not parent.has_children:
                            self.leaves.append(parent)
                    for parent in leaf.optional_parents:
                        parent.optional_children.remove(leaf)
                        if not parent.has_children:
                            self.leaves.append(parent)
                    removed_leaves.append(leaf)
            for leaf in removed_leaves:
                self.leaves.remove(leaf)

        num_nodes_pre = len(self.nodes)
        remove_leaves_one_pass()
        num_nodes_post = len(self.nodes)
        while num_nodes_pre != num_nodes_post:
            num_nodes_pre = num_nodes_post
            remove_leaves_one_pass()
            num_nodes_post = len(self.nodes)









class Node(object):
    def __init__(self, record):
        self.record = record
        self._constrains = tuple(MatchSpec(s).name for s in record.constrains)
        self.optional_parents = []
        self.optional_children = []
        self._depends = tuple(MatchSpec(s).name for s in record.depends)
        self.required_parents = []
        self.required_children = []
        self.specs = []

    def constrained_by(self, other):
        return other.record.name in self._constrains

    def depends_on(self, other):
        return other.record.name in self._depends

    has_children = property(lambda self: self.required_children or self.optional_children)
    has_parents = property(lambda self: self.required_parents or self.optional_parents)
    is_root = property(lambda self: self.has_children and not self.has_parents)
    is_leaf = property(lambda self: self.has_parents and not self.has_children)
    is_orphan = property(lambda self: not self.has_parents and not self.has_children)

