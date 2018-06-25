# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict

from .match_spec import EMPTY_NAMESPACE_EQUIVALENTS, MatchSpec
from ..common.compat import iteritems, itervalues, text_type

try:
    from cytoolz.itertoolz import groupby
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import groupby  # NOQA


class SpecsGroup(object):
    """
    A helper class for managing groups of specs, especially when dealing with both package
    name and namespace.
    """

    def __init__(self, initial_specs=()):
        self._specs_map = defaultdict(dict)  # package_name, namespace (or None), spec
        self._non_named_specs = set()
        for spec in initial_specs:
            self.add(spec)

    def add(self, spec):
        # If a namespace is not attached to the spec, clear all other existing specs and
        #   replace with the current spec.
        # If a namespace is attached to the spec, just add/replace that namespace entry.
        namespace = spec.namespace
        package_name = spec.name
        if not namespace:
            if package_name == '*':
                self._non_named_specs.add(spec)
            else:
                self._specs_map[package_name] = {None: spec}
        else:
            assert package_name, spec
            self._specs_map[package_name][namespace] = spec

    def remove(self, spec):
        # If namespace is not attached to the spec, remove all specs for the package name.
        # If a namespace is attached to the spec, just remove that namespace entry?
        namespace = spec.namespace
        package_name = spec.name
        if not namespace:
            if package_name == '*':
                self._non_named_specs.discard(spec)
            else:
                self._specs_map.pop(spec.name, None)
        else:
            spec_name = spec.name
            if spec_name in self._specs_map:
                self._specs_map[spec.name].pop(namespace, None)

    def remove_record_match(self, record):
        if record.name not in self._specs_map:
            return
        namespace_map = self._specs_map[record.name]
        remove_ns = tuple(ns for ns, spec in iteritems(namespace_map) if spec.match(record))
        for namespace in remove_ns:
            del namespace_map[namespace]
        if not namespace_map:
            del self._specs_map[record.name]

        remove_specs = (spec for spec in self._non_named_specs if spec.match(record))
        self._non_named_specs.difference_update(remove_specs)

    def update(self, specs_group):
        for package_name, spec_group in iteritems(specs_group._specs_map):
            self._specs_map[package_name].update(spec_group)
        self.merge()

    def merge(self):
        self._non_named_specs = set(MatchSpec.merge(self._non_named_specs))
        remove_these = []
        for package_name, namespace_map in iteritems(self._specs_map):
            if not namespace_map:
                remove_these.append(package_name)
            else:
                new_specs = MatchSpec.merge(itervalues(namespace_map))
                self._specs_map[package_name] = {spec.namespace: spec for spec in new_specs}
        for package_name in remove_these:
            del self._specs_map[package_name]

    def __str__(self):
        return "['%s']" % "', '".join(text_type(spec) for spec in self.iter_specs())

    def drop_specs_not_matching_records(self, records):
        new_specs = defaultdict(dict)
        grouped_records = groupby(lambda rec: rec.name, records)

        for package_name, spec_group in iteritems(self._specs_map):
            for namespace, spec in iteritems(spec_group):
                if any(spec.match(rec) for rec in grouped_records[package_name]):
                    new_specs[package_name][namespace] = spec

        self._specs_map.clear()
        self._specs_map.update(new_specs)

    def get_matches(self, record):
        return tuple(spec for spec in itervalues(self._specs_map[record.name])
                     if spec.match(record))

    def record_has_match(self, record):
        return bool(self.get_matches(record))

    def iter_specs(self):
        return iter(
            spec
            for spec_group in itervalues(self._specs_map)
            for spec in itervalues(spec_group)
        )

    def get_specs_by_name(self, package_name, namespace=None):
        if namespace not in EMPTY_NAMESPACE_EQUIVALENTS:
            try:
                return (self._specs_map[package_name][namespace],)
            except KeyError:
                return ()
        else:
            return tuple(itervalues(self._specs_map[package_name]))
