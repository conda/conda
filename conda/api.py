# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from .common.constants import NULL
from .core.package_cache_data import PackageCacheData as _PackageCacheData
from .core.prefix_data import PrefixData as _PrefixData
from .core.solve import Solver as _Solver, DepsModifier as _DepsModifier
from .core.subdir_data import SubdirData as _SubdirData
from .models.channel import Channel


DepsModifier = _DepsModifier


class Solver(object):

    def __init__(self, prefix, channels, subdirs=(), specs_to_add=(), specs_to_remove=()):
        self._internal = _Solver(prefix, channels, subdirs, specs_to_add, specs_to_remove)

    def solve_final_state(self, deps_modifier=NULL, prune=NULL, ignore_pinned=NULL,
                          force_remove=NULL):
        return self._internal.solve_final_state(deps_modifier, prune, ignore_pinned,
                                                force_remove)

    def solve_for_diff(self, deps_modifier=NULL, prune=NULL, ignore_pinned=NULL,
                       force_remove=NULL, force_reinstall=False):
        return self._internal.solve_for_diff(deps_modifier, prune, ignore_pinned,
                                             force_remove, force_reinstall)

    def solve_for_transaction(self, deps_modifier=NULL, prune=NULL, ignore_pinned=NULL,
                              force_remove=NULL, force_reinstall=False):
        return self._internal.solve_for_transaction(deps_modifier, prune, ignore_pinned,
                                                    force_remove, force_reinstall)


class SubdirData(object):

    def __init__(self, channel):
        assert isinstance(channel, Channel)
        assert channel.subdir
        assert not channel.package_filename
        self._internal = _SubdirData(channel)

    def query(self, package_ref_or_match_spec):
        return tuple(self._internal.query(package_ref_or_match_spec))

    @staticmethod
    def query_all(channels, subdirs, package_ref_or_match_spec):
        return tuple(_SubdirData.query_all(channels, subdirs, package_ref_or_match_spec))

    def iter_records(self):
        return self._internal.iter_records()

    def reload(self):
        self._internal = self._internal.reload()
        return self


class PackageCacheData(object):

    def __init__(self, pkgs_dir):
        self._internal = _PackageCacheData(pkgs_dir)

    def get(self, package_ref, default=NULL):
        return self._internal.get(package_ref, default)

    def query(self, package_ref_or_match_spec):
        return tuple(self._internal.query(package_ref_or_match_spec))

    @staticmethod
    def query_all(package_ref_or_match_spec, pkgs_dirs=None):
        return tuple(_PackageCacheData.query_all(package_ref_or_match_spec, pkgs_dirs))

    def iter_records(self):
        return self._internal.iter_records()

    @property
    def is_writable(self):
        return self._internal.is_writable

    @staticmethod
    def first_writable(pkgs_dirs=None):
        return PackageCacheData(_PackageCacheData.first_writable(pkgs_dirs).pkgs_dir)

    def reload(self):
        self._internal = self._internal.reload()
        return self


class PrefixData(object):

    def __init__(self, prefix_path):
        self._internal = _PrefixData(prefix_path)

    def get(self, package_ref, default=NULL):
        return self._internal.get(package_ref.name, default)

    def query(self, package_ref_or_match_spec):
        return tuple(self._internal.query(package_ref_or_match_spec))

    def iter_records(self):
        return self._internal.iter_records()

    @property
    def is_writable(self):
        return self._internal.is_writable

    def reload(self):
        self._internal = self._internal.reload()
        return self
