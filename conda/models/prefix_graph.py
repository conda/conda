# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from .enums import NoarchType
from .match_spec import MatchSpec
from .._vendor.boltons.setutils import IndexedSet
from ..base.context import context
from ..common.compat import iteritems, itervalues, odict, on_win
from ..exceptions import CyclicalDependencyError

log = getLogger(__name__)


class PrefixGraph(object):
    """
    A directed graph structure used for sorting packages (prefix_records) in prefixes and
    manipulating packages within prefixes (e.g. removing and pruning).

    The terminology used for edge direction is "parents" and "children" rather than "successors"
    and "predecessors". The parent nodes of a record are those records in the graph that
    match the record's "depends" field.  E.g. NodeA depends on NodeB, then NodeA is a child
    of NodeB, and NodeB is a parent of NodeA.  Nodes can have zero parents, or more than two
    parents.

    Most public methods mutate the graph.
    """

    def __init__(self, records, specs=()):
        specs = set(specs)
        records = tuple(records)
        graph = {}  # Dict[PrefixRecord, Set[PrefixRecord]]
        self.spec_matches = spec_matches = {}  # Dict[PrefixRecord, Set[MatchSpec]]
        for node in records:
            parent_match_specs = tuple(MatchSpec(d) for d in node.depends)
            parent_nodes = set(
                rec for rec in records if any(m.match(rec) for m in parent_match_specs)
            )
            graph[node] = parent_nodes
            matching_specs = IndexedSet(s for s in specs if s.match(node))
            if matching_specs:
                spec_matches[node] = matching_specs
        self.graph = graph
        self._toposort()

    def remove_spec(self, spec):
        """
        Remove all matching nodes, and any associated child nodes.

        Args:
            spec (MatchSpec):

        Returns:
            Tuple[PrefixRecord]: The removed nodes.

        """
        node_matches = set(node for node in self.graph if spec.match(node))

        # If the spec was a track_features spec, then we need to also remove every
        # package with a feature that matches the track_feature.
        for feature_name in spec.get_raw_value('track_features') or ():
            feature_spec = MatchSpec(features=feature_name)
            node_matches.update(node for node in self.graph if feature_spec.match(node))

        remove_these = set()
        for node in node_matches:
            remove_these.add(node)
            remove_these.update(self.all_descendants(node))
        remove_these = tuple(filter(
            lambda node: node in remove_these,
            self.graph
        ))
        for node in remove_these:
            self._remove_node(node)
        self._toposort()
        return tuple(remove_these)

    def remove_youngest_descendant_nodes_with_specs(self):
        """
        A specialized method used to determine only dependencies of requested specs.

        Returns:
            Tuple[PrefixRecord]: The removed nodes.

        """
        graph = self.graph
        spec_matches = self.spec_matches
        inverted_graph = {
            node: set(key for key in graph if node in graph[key])
            for node in graph
        }
        youngest_nodes_with_specs = tuple(node for node, children in iteritems(inverted_graph)
                                          if not children and node in spec_matches)
        removed_nodes = tuple(filter(
            lambda node: node in youngest_nodes_with_specs,
            self.graph
        ))
        for node in removed_nodes:
            self._remove_node(node)
        self._toposort()
        return removed_nodes

    @property
    def records(self):
        return iter(self.graph)

    def prune(self):
        """Prune back all packages until all child nodes are anchored by a spec.

        Returns:
            Tuple[PrefixRecord]: The pruned nodes.

        """
        graph = self.graph
        spec_matches = self.spec_matches
        original_order = tuple(self.graph)

        removed_nodes = set()
        while True:
            inverted_graph = {
                node: set(key for key in graph if node in graph[key])
                for node in graph
            }
            prunable_nodes = tuple(node for node, children in iteritems(inverted_graph)
                                   if not children and node not in spec_matches)
            if not prunable_nodes:
                break
            for node in prunable_nodes:
                removed_nodes.add(node)
                self._remove_node(node)

        removed_nodes = tuple(filter(
            lambda node: node in removed_nodes,
            original_order
        ))
        self._toposort()
        return removed_nodes

    def get_node_by_name(self, name):
        return next(rec for rec in self.graph if rec.name == name)

    def all_descendants(self, node):
        graph = self.graph
        inverted_graph = {
            node: set(key for key in graph if node in graph[key])
            for node in graph
        }

        nodes = [node]
        nodes_seen = set()
        q = 0
        while q < len(nodes):
            for child_node in inverted_graph[nodes[q]]:
                if child_node not in nodes_seen:
                    nodes_seen.add(child_node)
                    nodes.append(child_node)
            q += 1
        return tuple(
            filter(
                lambda node: node in nodes_seen,
                graph
            )
        )

    def all_ancestors(self, node):
        graph = self.graph
        nodes = [node]
        nodes_seen = set()
        q = 0
        while q < len(nodes):
            for parent_node in graph[nodes[q]]:
                if parent_node not in nodes_seen:
                    nodes_seen.add(parent_node)
                    nodes.append(parent_node)
            q += 1
        return tuple(
            filter(
                lambda node: node in nodes_seen,
                graph
            )
        )

    def _remove_node(self, node):
        """ Removes this node and all edges referencing it. """
        graph = self.graph
        if node not in graph:
            raise KeyError('node %s does not exist' % node)
        graph.pop(node)
        self.spec_matches.pop(node, None)

        for node, edges in iteritems(graph):
            if node in edges:
                edges.remove(node)

    def _toposort(self):
        graph_copy = odict((node, IndexedSet(parents)) for node, parents in iteritems(self.graph))
        self._toposort_prepare_graph(graph_copy)
        if context.allow_cycles:
            sorted_nodes = tuple(self._topo_sort_handle_cycles(graph_copy))
        else:
            sorted_nodes = tuple(self._toposort_raise_on_cycles(graph_copy))
        original_graph = self.graph
        self.graph = odict((node, original_graph[node]) for node in sorted_nodes)
        return sorted_nodes

    @classmethod
    def _toposort_raise_on_cycles(cls, graph):
        if not graph:
            return

        while True:
            no_parent_nodes = IndexedSet(sorted(
                (node for node, parents in iteritems(graph) if len(parents) == 0),
                key=lambda x: x.name
            ))
            if not no_parent_nodes:
                break

            for node in no_parent_nodes:
                yield node
                graph.pop(node, None)

            for parents in itervalues(graph):
                parents -= no_parent_nodes

        if len(graph) != 0:
            raise CyclicalDependencyError(tuple(graph))

    @classmethod
    def _topo_sort_handle_cycles(cls, graph):
        # remove edges that point directly back to the node
        for k, v in iteritems(graph):
            v.discard(k)

        # disconnected nodes go first
        nodes_that_are_parents = set(node for parents in itervalues(graph) for node in parents)
        nodes_without_parents = (node for node in graph if not graph[node])
        disconnected_nodes = sorted(
            (node for node in nodes_without_parents if node not in nodes_that_are_parents),
            key=lambda x: x.name
        )
        for node in disconnected_nodes:
            yield node

        t = cls._toposort_raise_on_cycles(graph)

        while True:
            try:
                value = next(t)
                yield value
            except CyclicalDependencyError as e:
                # TODO: Turn this into a warning, but without being too annoying with
                #       multiple messages.  See https://github.com/conda/conda/issues/4067
                log.debug('%r', e)

                yield cls._toposort_pop_key(graph)

                t = cls._toposort_raise_on_cycles(graph)
                continue

            except StopIteration:
                return

    @staticmethod
    def _toposort_pop_key(graph):
        """
        Pop an item from the graph that has the fewest parents.
        In the case of a tie, use the node with the alphabetically-first package name.
        """
        node_with_fewest_parents = sorted(
            (len(parents), node.name, node) for node, parents in iteritems(graph)
        )[0][2]
        graph.pop(node_with_fewest_parents)

        for parents in itervalues(graph):
            parents.discard(node_with_fewest_parents)

        return node_with_fewest_parents

    @staticmethod
    def _toposort_prepare_graph(graph):
        # There are currently at least three special cases to be aware of.

        # 1. Remove any circular dependency between python and pip. This typically comes about
        #    because of the add_pip_as_python_dependency configuration parameter.
        for node in graph:
            if node.name == "python":
                parents = graph[node]
                for parent in tuple(parents):
                    if parent.name == 'pip':
                        parents.remove(parent)

        if on_win:
            # 2. Special case code for menuinst.
            #    Always link/unlink menuinst first/last on windows in case a subsequent
            #    package tries to import it to create/remove a shortcut.
            menuinst_node = next((node for node in graph if node.name == 'menuinst'), None)
            python_node = next((node for node in graph if node.name == 'python'), None)
            if menuinst_node:
                # add menuinst as a parent if python is a parent and the node
                # isn't a parent of menuinst
                assert python_node is not None
                menuinst_parents = graph[menuinst_node]
                for node, parents in iteritems(graph):
                    if python_node in parents and node not in menuinst_parents:
                        parents.add(menuinst_node)

            # 3. On windows, python noarch packages need an implicit dependency on conda added, if
            #    conda is in the list of packages for the environment.  Python noarch packages
            #    that have entry points use conda's own conda.exe python entry point binary. If
            #    conda is going to be updated during an operation, the unlink / link order matters.
            #    See issue #6057.
            conda_node = next((node for node in graph if node.name == 'conda'), None)
            if conda_node:
                # add conda as a parent if python is a parent and node isn't a parent of conda
                conda_parents = graph[conda_node]
                for node, parents in iteritems(graph):
                    if (hasattr(node, 'noarch') and node.noarch == NoarchType.python
                            and node not in conda_parents):
                        parents.add(conda_node)


#     def dot_repr(self, title=None):  # pragma: no cover
#         # graphviz DOT graph description language
#
#         builder = ['digraph g {']
#         if title:
#             builder.append('  labelloc="t";')
#             builder.append('  label="%s";' % title)
#         builder.append('  size="10.5,8";')
#         builder.append('  rankdir=BT;')
#         for node in self.get_nodes_ordered_from_roots():
#             label = "%s %s" % (node.record.name, node.record.version)
#             if node.specs:
#                 # TODO: combine?
#                 spec = next(iter(node.specs))
#                 label += "\\n%s" % ("?%s" if spec.optional else "%s") % spec
#             if node.is_orphan:
#                 shape = "box"
#             elif node.is_root:
#                 shape = "invhouse"
#             elif node.is_leaf:
#                 shape = "house"
#             else:
#                 shape = "ellipse"
#             builder.append('  "%s" [label="%s", shape=%s];' % (node.record.name, label, shape))
#             for child in node.required_children:
#                 builder.append('    "%s" -> "%s";' % (child.record.name, node.record.name))
#             for child in node.optional_children:
#                 builder.append('    "%s -> "%s" [color=lightgray];' % (child.record.name,
#                                                                        node.record.name))
#         builder.append('}')
#         return '\n'.join(builder)
#
#     def format_url(self):  # pragma: no cover
#         return "https://condaviz.glitch.me/%s" % url_quote(self.dot_repr())
#
#     def request_svg(self):  # pragma: no cover
#         from tempfile import NamedTemporaryFile
#         import requests
#         from ..common.compat import ensure_binary
#         response = requests.post("https://condaviz.glitch.me/post",
#                                  data={"digraph": self.dot_repr()})
#         response.raise_for_status()
#         with NamedTemporaryFile(suffix='.svg', delete=False) as fh:
#             fh.write(ensure_binary(response.text))
#         print("saved to: %s" % fh.name, file=sys.stderr)
#         return fh.name
#
#     def open_url(self):  # pragma: no cover
#         import webbrowser
#         from ..common.url import path_to_url
#         location = self.request_svg()
#         try:
#             browser = webbrowser.get("safari")
#         except webbrowser.Error:
#             browser = webbrowser.get()
#         browser.open_new_tab(path_to_url(location))


# if __name__ == "__main__":
#     from ..core.prefix_data import PrefixData
#     from ..history import History
#     prefix = sys.argv[1]
#     records = PrefixData(prefix).iter_records()
#     specs = itervalues(History(prefix).get_requested_specs_map())
#     PrefixDag(records, specs).open_url()
