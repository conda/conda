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
        self.records = tuple(records)
        self.specs = tuple(specs)

        self.nodes = nodes = []
        self.roots = roots = []
        self.leaves = leaves = []
        self.orphans = orphans = []
        self.spec_matches = spec_matches = defaultdict(list)

        for record in records:
            new_node = Node(record)
            nodes.append(new_node)
            for old_node in nodes:
                if new_node.depends_on(old_node):
                    new_node.parents.append(old_node)
                    old_node.children.append(new_node)

        for node in nodes:
            for spec in specs:
                if spec.match(node.record):
                    node.specs.append(spec)
                    spec_matches[spec].append(node)
            if not node.parents and not node.children:
                orphans.append(node)
            elif not node.parents:
                roots.append(node)
            elif not node.children:
                leaves.append(node)


class Node(object):
    def __init__(self, record):
        self.record = record
        self._depends = tuple(MatchSpec(s).name for s in record.depends)
        self.parents = []
        self.children = []
        self.specs = []

    def depends_on(self, other):
        return other.record.name in self._depends
