# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict

from .channel import all_channel_urls
from .match_spec import MatchSpec
from ..common.compat import iteritems, itervalues, text_type
from ..exceptions import PackagesNotFoundError

try:
    from cytoolz.itertoolz import concatv, groupby
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concatv, groupby  # NOQA


class SpecsGroup(object):
    """
    A helper class for managing groups of specs, especially when dealing with both package
    name and namespace.
    """

    def __init__(self, initial_specs=()):
        self._required_specs_map = defaultdict(dict)  # package_name, namespace (or None), spec
        self._optional_specs_map = defaultdict(dict)  # package_name, namespace (or None), spec
        self._non_named_specs = set()
        for spec in initial_specs:
            self.add_override(spec)

    def add_override(self, spec):
        # If a namespace is not attached to the spec, clear all other existing specs and
        #   replace with the current spec.
        # If a namespace is attached to the spec, just add/replace that namespace entry.
        namespace = spec.namespace
        package_name = spec.name
        _specs_map = self._optional_specs_map if spec.optional else self._required_specs_map
        if package_name == '*':
            self._non_named_specs.add(spec)
        else:
            _specs_map[package_name][namespace] = spec

    def remove(self, spec):
        # If namespace is not attached to the spec, remove all specs for the package name.
        # If a namespace is attached to the spec, just remove that namespace entry?
        namespace = spec.namespace
        package_name = spec.name
        _specs_map = self._optional_specs_map if spec.optional else self._required_specs_map
        if package_name == '*':
            self._non_named_specs.discard(spec)
        else:
            _specs_map.get(package_name, {}).pop(namespace, None)

    def remove_record_match(self, record):
        if record.name not in self._required_specs_map:
            return
        namespace_map = self._required_specs_map[record.name]
        remove_ns = tuple(ns for ns, spec in iteritems(namespace_map) if spec.match(record))
        for namespace in remove_ns:
            del namespace_map[namespace]
        if not namespace_map:
            del self._required_specs_map[record.name]

        remove_specs = (spec for spec in self._non_named_specs if spec.match(record))
        self._non_named_specs.difference_update(remove_specs)

    def update(self, specs_group):
        for spec in specs_group.iter_specs():
            self.add_override(spec)
        self.merge()

    def merge(self):
        self._non_named_specs = set(MatchSpec.merge(self._non_named_specs))
        remove_these = []
        for package_name, namespace_map in iteritems(self._required_specs_map):
            if not namespace_map:
                remove_these.append(package_name)
            else:
                self._required_specs_map[package_name] = {
                    spec.namespace: spec for spec in MatchSpec.merge(itervalues(namespace_map))
                }
        for package_name in remove_these:
            del self._required_specs_map[package_name]
        remove_these = []
        for package_name, namespace_map in iteritems(self._optional_specs_map):
            if not namespace_map:
                remove_these.append(package_name)
            else:
                self._optional_specs_map[package_name] = {
                    spec.namespace: spec for spec in MatchSpec.merge(itervalues(namespace_map))
                }
        for package_name in remove_these:
            del self._optional_specs_map[package_name]

    def __str__(self):
        return "('%s')" % "', '".join(text_type(spec) for spec in self.iter_specs())

    def __repr__(self):
        return "SpecsGroup(('%s'))" % "', '".join(text_type(spec) for spec in self.iter_specs())

    def drop_specs_not_matching_records(self, records):
        grouped_records = groupby(lambda rec: rec.name, records)

        new_specs = defaultdict(dict)
        for package_name, spec_group in iteritems(self._required_specs_map):
            for namespace, spec in iteritems(spec_group):
                if any(spec.match(rec) for rec in grouped_records[package_name]):
                    new_specs[package_name][namespace] = spec
        self._required_specs_map.clear()
        self._required_specs_map.update(new_specs)

        new_specs = defaultdict(dict)
        for package_name, spec_group in iteritems(self._optional_specs_map):
            for namespace, spec in iteritems(spec_group):
                if any(spec.match(rec) for rec in grouped_records[package_name]):
                    new_specs[package_name][namespace] = spec
        self._optional_specs_map.clear()
        self._optional_specs_map.update(new_specs)

    def get_matches(self, record):
        return tuple(spec for spec in self.iter_specs() if spec.match(record))

    def record_has_match(self, record):
        return bool(self.get_matches(record))

    def iter_specs(self):
        return concatv(
            (spec
             for ns_map in concatv(itervalues(self._required_specs_map),
                                   itervalues(self._optional_specs_map))
             for spec in itervalues(ns_map)),
            self._non_named_specs,
        )

    def get_specs_by_name(self, package_name, namespace=None):
        matches = tuple(spec for spec in self.iter_specs() if spec.name == package_name)
        if namespace:
            matches = tuple(spec for spec in matches if spec.namespace == namespace)
        return matches

    def declared_namespaces(self):
        return frozenset(ns for ns in (spec.namespace for spec in self.iter_specs()) if ns)

    def non_namespaced_specs(self):
        return tuple(spec for spec in self.iter_specs() if not spec.namespace and spec.name != '*')

    def attach_namespaces(self, r):
        # first pass, determine all non-ambiguous cases
        all_required_namespaces = set()
        ambiguous_cases = {}
        specs_not_found = set()
        for spec in self.non_namespaced_specs():
            required_namespaces = r.required_namespaces(spec)
            if len(required_namespaces) == 1:
                new_spec, namespace_dependencies = required_namespaces.popitem()
                self.remove(spec)
                self.add_override(new_spec)
                all_required_namespaces.add(new_spec.namespace)
                all_required_namespaces.update(namespace_dependencies)
            elif not required_namespaces:
                specs_not_found.add(spec)
            else:
                # ambiguous situation
                ambiguous_cases[spec] = required_namespaces
        if specs_not_found:
            raise PackagesNotFoundError(
                tuple(sorted(str(s) for s in specs_not_found)),
                all_channel_urls(r.channels)
            )

        # second pass, try intersection with 'global', then intersection, then use union
        if not ambiguous_cases:
            return

        namespace_sets = tuple(set(spec.namespace for spec in case)
                               for case in itervalues(ambiguous_cases))
        intersecting_namespaces = set.intersection(*namespace_sets) & all_required_namespaces
        if not intersecting_namespaces:
            intersecting_namespaces = set.intersection(*namespace_sets) & {"global"}
            if not intersecting_namespaces:
                intersecting_namespaces = set.intersection(*namespace_sets)
                if not intersecting_namespaces:
                    intersecting_namespaces = set.union(*namespace_sets)
        for spec, required_namespaces in iteritems(ambiguous_cases):
            ns_map = {spec.namespace: spec for spec in required_namespaces}
            self.remove(spec)
            for namespace in intersecting_namespaces:
                new_spec = ns_map[namespace]
                namespace_dependencies = required_namespaces[new_spec]
                self.add_override(new_spec)
                all_required_namespaces.add(new_spec.namespace)
                all_required_namespaces.update(namespace_dependencies)

        self.merge()
