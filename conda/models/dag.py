# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict, deque
from logging import getLogger
import sys
from weakref import WeakSet, proxy

from conda.common.compat import odict
from .match_spec import MatchSpec
from .._vendor.boltons.setutils import IndexedSet
from ..common.compat import itervalues, iteritems
from ..common.url import quote as url_quote

try:
    from cytoolz.functoolz import excepts
    from cytoolz.itertoolz import concatv
except ImportError:
    from .._vendor.toolz.functoolz import excepts  # NOQA
    from .._vendor.toolz.itertoolz import concatv  # NOQA

log = getLogger(__name__)


class PrefixDag2(object):
    # https://github.com/thieman/py-dag/blob/master/dag/__init__.py

    def __init__(self, records, specs):
        self.graph = graph = {}
        self.spec_matches = spec_matches = {}
        for record in records:
            matchers = tuple(MatchSpec(d) for d in record.depends)
            dependents = IndexedSet(sorted(
                (rec for rec in records if any(m.match(rec) for m in matchers)),
                key=lambda x: x._pkey
            ))
            graph[record] = dependents
            matching_specs = IndexedSet(s for s in specs if s.match(record))
            if matching_specs:
                spec_matches[record] = matching_specs

    def remove_spec(self, spec):
        remove_these = tuple(node for node in self.graph if spec.match(node))
        for node in remove_these:
            self.delete_node(node)

    def remove_root_nodes_with_specs(self):
        spec_matches = self.spec_matches
        roots_with_specs = tuple(node for node in self.all_roots() if node in spec_matches)
        for node in roots_with_specs:
            self.delete_node(node)

    @property
    def records(self):
        return iter(self.graph)

    def prune(self):
        # remove orphans without specs
        # remove roots without specs
        orphans = set(self.all_orphans())
        roots_wo_specs = set(node for node in self.all_roots() if node not in self.spec_matches)
        for node in orphans | roots_wo_specs:
            self.delete_node(node)

    def get_node_by_name(self, name):
        return next(rec for rec in self.graph if rec.name == name)

    def delete_node(self, node):
        """ Deletes this node and all edges referencing it. """
        graph = self.graph
        if node not in graph:
            raise KeyError('node %s does not exist' % node)
        graph.pop(node)
        self.spec_matches.pop(node, None)

        for node, edges in iteritems(graph):
            if node in edges:
                edges.remove(node)

    def all_leaves(self):
        """ Return a list of all leaves (nodes with no downstreams) """
        graph = self.graph
        return [key for key in graph if not graph[key]]

    def predecessors(self, node):
        """ Returns a list of all predecessors of the given node """
        graph = self.graph
        return [key for key in graph if node in graph[key]]

    def all_predecessors(self, node):
        # all children
        nodes = [node]
        nodes_seen = set()
        i = 0
        while i < len(nodes):
            predecessors = self.predecessors(nodes[i])
            for predecessor_node in predecessors:
                if predecessor_node not in nodes_seen:
                    nodes_seen.add(predecessor_node)
                    nodes.append(predecessor_node)
            i += 1
        return list(
            filter(
                lambda node: node in nodes_seen,
                self.topological_sort()
            )
        )

    def all_roots(self):
        """ Returns a list of all nodes in the graph with no dependencies. """
        # independent nodes, root nodes, nodes with no dependencies
        graph = self.graph
        dependent_nodes = set(
            node for dependents in itervalues(graph) for node in dependents
        )
        return [node for node in graph.keys() if node not in dependent_nodes]

    def all_orphans(self):
        leaves = self.all_leaves()
        roots = self.all_roots()
        return [node for node in leaves if node in roots]

    def children(self, node):
        # children depend on parents
        # children of this node are the records that depend on this node
        graph = self.graph
        return tuple(node for node in graph if node in graph[node])

    def parents(self, node):
        # just record.depends
        return tuple(self.graph[node])

    def oldest_ascendants(self):
        pass

    def youngest_descendants(self):
        pass

    def downstream(self, node):
        """ Returns a list of all nodes this node has edges towards. """
        graph = self.graph
        if node not in graph:
            raise KeyError('node %s is not in graph' % node)
        return list(graph[node])

    def all_downstreams(self, node):
        """Returns a list of all nodes ultimately downstream
        of the given node in the dependency graph, in
        topological order."""
        nodes = [node]
        nodes_seen = set()
        i = 0
        while i < len(nodes):
            downstreams = self.downstream(nodes[i])
            for downstream_node in downstreams:
                if downstream_node not in nodes_seen:
                    nodes_seen.add(downstream_node)
                    nodes.append(downstream_node)
            i += 1
        return list(
            filter(
                lambda node: node in nodes_seen,
                self.topological_sort()
            )
        )

    def topological_sort(self):
        graph = self.graph
        in_degree = {}
        for u in graph:
            in_degree[u] = 0

        for u in graph:
            for v in graph[u]:
                in_degree[v] += 1

        queue = deque()
        for u in in_degree:
            if in_degree[u] == 0:
                queue.appendleft(u)

        l = []
        while queue:
            u = queue.pop()
            l.append(u)
            for v in graph[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.appendleft(v)

        if len(l) == len(graph):
            self.graph = odict((node, graph[node]) for node in l)
            return l
        else:
            raise ValueError('graph is not acyclic')




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

        self.nodes = self.get_nodes_ordered_from_roots()
        print([str(n) for n in self.nodes])

    def get_node_by_name(self, name):
        return next((node for node in self.nodes if node.record.name == name), None)

    def add_spec(self, spec):
        for node in self.nodes:
            if spec.match(node.record):
                node.specs.add(spec)
                self.spec_matches[spec].append(node)

    def remove_spec(self, spec):
        removed = []

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

        # if spec is a provides_features spec, then we also need to remove packages that match
        # those features
        for feature_name in spec.get_raw_value('track_features') or ():
            feature_spec = MatchSpec(features=feature_name)
            while True:
                for node in self.nodes:
                    if feature_spec.match(node.record):
                        removed.extend(self.remove_node_and_children(node))
                        break
                else:
                    break

        return removed

    def get_nodes_ordered_from_roots(self):
        name_key = lambda node: node.record.name
        ordered = IndexedSet(sorted((node for node in self.nodes if node.is_orphan), key=name_key))
        queue = deque(sorted((node for node in self.nodes if node.is_root), key=name_key))
        while queue:
            # Can node be added?
            # Are all parents already added?
            # If all parent nodes are already in the result, add the node to the result and
            #   add all the node's children to the queue.
            # Otherwise, put the node on the end of the queue
            node = queue.popleft()
            parents = concatv(node.required_parents, node.optional_parents)
            if all(parent in ordered for parent in parents):
                ordered.add(node)
                queue.extend(node for node in sorted(node.required_children, key=name_key)
                             if node not in ordered)
                queue.extend(node for node in sorted(node.optional_children, key=name_key)
                             if node not in ordered)
            else:
                queue.append(node)

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
            children = concatv(node.required_children, node.optional_children)
            if all(child in ordered for child in children):
                ordered.add(node)
                queue.extend(node for node in sorted(node.required_parents, key=name_key)
                             if node not in ordered)
                queue.extend(node for node in sorted(node.optional_parents, key=name_key)
                             if node not in ordered)
            else:
                queue.append(node)
        return list(ordered)

    def order_nodes_from_roots(self, nodes):
        """
        Returns:
            A deterministically sorted breadth-first ordering of nodes, starting from root nodes.
            Orphan nodes are prepended to the breadth-first ordering.
        """
        return list(sorted(nodes, key=lambda n: self.nodes.index(n)))

    def remove_node_and_children(self, node):
        # yields records for the removed nodes
        nodes = self.order_nodes_from_roots(node.all_descendants())
        for child in nodes:
            for record in self.remove_node_and_children(child):
                if record:
                    yield record
        record = self.remove(node)
        if record:
            yield record

    def dot_repr(self, title=None):  # pragma: no cover
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
                spec = next(iter(node.specs))
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

    def format_url(self):  # pragma: no cover
        return "https://condaviz.glitch.me/%s" % url_quote(self.dot_repr())

    def request_svg(self):  # pragma: no cover
        from tempfile import NamedTemporaryFile
        import requests
        from ..common.compat import ensure_binary
        response = requests.post("https://condaviz.glitch.me/post",
                                 data={"digraph": self.dot_repr()})
        response.raise_for_status()
        with NamedTemporaryFile(suffix='.svg', delete=False) as fh:
            fh.write(ensure_binary(response.text))
        print("saved to: %s" % fh.name, file=sys.stderr)
        return fh.name

    def open_url(self):  # pragma: no cover
        import webbrowser
        from ..common.url import path_to_url
        location = self.request_svg()
        try:
            browser = webbrowser.get("safari")
        except webbrowser.Error:
            browser = webbrowser.get()
        browser.open_new_tab(path_to_url(location))

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
        if node in self.nodes:
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
        self.record = proxy(record)
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

    def __str__(self):
        return self.record.dist_str()

    def constrained_by(self, other):
        return other.record.name in self._constrains

    def depends_on(self, other):
        return other.record.name in self._depends

    def all_descendants(self):
        descendents = IndexedSet()
        queue = deque(concatv(self.required_children, self.optional_children))
        while queue:
            node = queue.popleft()
            descendents.add(node)
            queue.extend(child for child in concatv(node.required_children, node.optional_children)
                         if child not in descendents)
        return descendents

    def all_ascendants(self):
        ascendants = IndexedSet()
        queue = deque(concatv(self.required_parents, self.optional_parents))
        while queue:
            node = queue.popleft()
            ascendants.add(node)
            queue.extend(parent for parent in concatv(node.required_parents, node.optional_parents)
                         if parent not in ascendants)
        return ascendants

    has_children = property(lambda self: self.required_children or self.optional_children)
    has_parents = property(lambda self: self.required_parents or self.optional_parents)
    is_root = property(lambda self: self.has_children and not self.has_parents)
    is_leaf = property(lambda self: self.has_parents and not self.has_children)
    is_orphan = property(lambda self: not self.has_parents and not self.has_children)


if __name__ == "__main__":
    from ..core.prefix_data import PrefixData
    from ..history import History
    prefix = sys.argv[1]
    records = PrefixData(prefix).iter_records()
    specs = itervalues(History(prefix).get_requested_specs_map())
    PrefixDag(records, specs).open_url()
