# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict, deque
from logging import getLogger
from weakref import WeakSet

from .match_spec import MatchSpec
from .._vendor.boltons.setutils import IndexedSet
from ..common.url import quote as url_quote

try:
    from cytoolz.functoolz import excepts
except ImportError:
    from .._vendor.toolz.functoolz import excepts  # NOQA

log = getLogger(__name__)


class PrefixDag(object):
    # This is in conda.models and not conda.common because it isn't general and assumes
    #   knowledge of record and match_spec structure.
    # Not immutable.  Also optimizing for convenience, not performance.
    #   For < ~1,000 packages, performance shouldn't be a problem.

    def __init__(self, records, specs):
        self.nodes = []
        self.spec_matches = defaultdict(list)

        for record in records:
            Node(self, record)

        for spec in specs:
            self.add_spec(spec)

    def get_node_by_name(self, name):
        return next((node for node in self.nodes if node.record.name == name), None)

    def add_spec(self, spec):
        for node in self.nodes:
            if spec.match(node.record):
                node.specs.add(spec)
                self.spec_matches[spec].append(node)

    def remove_spec(self, spec):
        removed = []
        self.nodes = self.get_nodes_ordered_from_roots()

        while True:
            # This while True pattern is needed because when we remove nodes, we break the view
            # of the graph as given by the self.nodes iterator.  Thus, if we do a removal, we
            # need to break the current for loop and re-enter with a new self.nodes view. The
            # removal is complete when we iterate through all nodes without a removal. Doing
            # a single sort of the nodes at the top of this method should minimize the number
            # of iterations we have to make through the for loop.
            for node in self.nodes:
                if spec.match(node.record):
                    removed.extend(self.remove_node_and_children(node))
                    break
            else:
                break

        # if spec is a track_features spec, then we also need to remove packages that match
        # those features
        for feature in spec.get_raw_value('track_features') or ():
            feature_spec = MatchSpec(features=feature)
            while True:
                for node in self.nodes:
                    if feature_spec.match(node.record):
                        removed.extend(self.remove_node_and_children(node))
                        break
                else:
                    break

        return removed

    def get_nodes_ordered_from_roots(self):
        """
        Returns:
            A deterministically sorted breadth-first ordering of nodes, starting from root nodes.
            Orphan nodes are prepended to the breadth-first ordering.
        """
        name_key = lambda node: node.record.name
        ordered = IndexedSet(sorted((node for node in self.nodes if node.is_orphan), key=name_key))
        queue = deque(sorted((node for node in self.nodes if node.is_root), key=name_key))
        while queue:
            node = queue.popleft()
            ordered.add(node)
            queue.extend(node for node in sorted(node.required_children, key=name_key)
                         if node not in ordered)
            queue.extend(node for node in sorted(node.optional_children, key=name_key)
                         if node not in ordered)
        return list(ordered)

    def get_nodes_ordered_from_leaves(self):
        """
        Returns:
            A deterministically sorted breadth-first ordering of nodes, starting from leaf nodes.
            Orphan nodes are prepended to the breadth-first ordering.
        """
        name_key = lambda node: node.record.name
        ordered = IndexedSet(sorted((node for node in self.nodes if node.is_orphan), key=name_key))
        queue = deque(sorted((node for node in self.nodes if node.is_leaf), key=name_key))
        while queue:
            node = queue.popleft()
            ordered.add(node)
            queue.extend(node for node in sorted(node.required_parents, key=name_key)
                         if node not in ordered)
            queue.extend(node for node in sorted(node.optional_parents, key=name_key)
                         if node not in ordered)
        return list(ordered)

    def order_nodes_leaves_last(self, nodes):
        name_key = lambda node: node.record.name
        ordered = IndexedSet(sorted((node for node in nodes if node.is_orphan), key=name_key))
        queue = deque(sorted((node for node in nodes if node.is_leaf), key=name_key))
        while queue:
            node = queue.popleft()
            ordered.add(node)
            queue.extend(node for node in sorted(node.required_children, key=name_key)
                         if node not in ordered)
            queue.extend(node for node in sorted(node.optional_children, key=name_key)
                         if node not in ordered)
        return list(ordered)

    def remove_node_and_children(self, node):
        nodes = self.order_nodes_leaves_last(node.all_descendants())
        for child in nodes:
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
        for node in self.get_nodes_ordered_from_roots():
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
                builder.append('    "%s -> "%s" [color=lightgray];' % (child.record.name,
                                                                       node.record.name))
        builder.append('}')
        return '\n'.join(builder)

    def format_url(self):
        return "https://condaviz.glitch.me/%s" % url_quote(self.dot_repr())

    def open_url(self):
        import webbrowser
        # TODO: remove this "safari" specifier once Apple gets its act together and
        # releases macOS 10.12.6
        browser = webbrowser.get("safari")
        browser.open_new_tab(self.format_url())
        # webbrowser.open_new_tab(self.format_url())

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
                if not leaf.specs or any(spec.optional for spec in leaf.specs):
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

    def remove_leaf_nodes_with_specs(self):
        leaves = tuple(self.leaves)
        for leaf in leaves:
            if leaf.specs:
                self.remove(leaf)


class Node(object):

    def __init__(self, dag, record):
        self.record = record
        self._constrains = tuple(MatchSpec(s).name for s in record.constrains)
        self._depends = tuple(MatchSpec(s).name for s in record.depends)

        self.optional_parents = WeakSet()
        self.optional_children = WeakSet()
        self.required_parents = WeakSet()
        self.required_children = WeakSet()
        self.specs = WeakSet()

        for old_node in dag.nodes:
            if self.constrained_by(old_node):
                self.optional_parents.add(old_node)
                old_node.optional_children.add(self)
            elif self.depends_on(old_node):
                self.required_parents.add(old_node)
                old_node.required_children.add(self)
            elif old_node.constrained_by(self):
                old_node.optional_parents.add(self)
                self.optional_children.add(old_node)
            elif old_node.depends_on(self):
                old_node.required_parents.add(self)
                self.required_children.add(old_node)

        for spec in dag.spec_matches:
            if spec.match(record):
                self.specs.add(spec)
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
        return tuple(_all_descendants())

    def all_ascendants(self):
        def _all_descendants():
            for parent in self.required_parents:
                for gparent in parent.required_parents:
                    yield gparent
                yield parent
            for parent in self.optional_parents:
                for gparent in parent.optional_parents:
                    yield gparent
                yield parent
        return tuple(_all_descendants())

    has_children = property(lambda self: self.required_children or self.optional_children)
    has_parents = property(lambda self: self.required_parents or self.optional_parents)
    is_root = property(lambda self: self.has_children and not self.has_parents)
    is_leaf = property(lambda self: self.has_parents and not self.has_children)
    is_orphan = property(lambda self: not self.has_parents and not self.has_children)
