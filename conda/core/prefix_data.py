# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from fnmatch import filter as fnmatch_filter
from logging import getLogger
<<<<<<< HEAD
from os import listdir
from os.path import basename, dirname, isdir, isfile, join, lexists
=======
from os.path import basename, isdir, isfile, join, lexists
>>>>>>> Add code to handle python dists (remove distlib dependency) and refactor code

from ..base.constants import CONDA_TARBALL_EXTENSION, PREFIX_MAGIC_FILE
from ..base.context import context
from ..common.compat import JSONDecodeError, itervalues, string_types, with_metaclass
from ..common.constants import NULL
from ..common.path import get_python_site_packages_short_path, win_path_ok
from ..common.serialize import json_load
from ..core.python_dist import (get_conda_anchor_files_and_records, get_python_records,
                                get_site_packages_anchor_files)
from ..exceptions import (BasicClobberError, CondaDependencyError, CorruptedEnvironmentError,
                          maybe_raise)
from ..gateways.disk.create import write_as_json_to_file
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.test import file_path_is_writable
from ..models.match_spec import MatchSpec
from ..models.prefix_graph import PrefixGraph
from ..models.records import PackageRecord, PrefixRecord

try:
    from cytoolz.itertoolz import concat, concatv
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concat, concatv  # NOQA


log = getLogger(__name__)


class PrefixDataType(type):
    """Basic caching of PrefixData instance objects."""

    def __call__(cls, prefix_path, pip_interop_enabled=None):
        if prefix_path in PrefixData._cache_:
            return PrefixData._cache_[prefix_path]
        elif isinstance(prefix_path, PrefixData):
            return prefix_path
        else:
            prefix_data_instance = super(PrefixDataType, cls).__call__(prefix_path,
                                                                       pip_interop_enabled)
            PrefixData._cache_[prefix_path] = prefix_data_instance
            return prefix_data_instance


@with_metaclass(PrefixDataType)
class PrefixData(object):
    _cache_ = {}

    def __init__(self, prefix_path, pip_interop_enabled=None):
        # pip_interop_enabled is a temporary paramater; DO NOT USE
        # TODO: when removing pip_interop_enabled, also remove from meta class
        self.prefix_path = prefix_path
        self.__prefix_records = None
        self.__is_writable = NULL
        self._pip_interop_enabled = (context.pip_interop_enabled
                                     if pip_interop_enabled is None
                                     else pip_interop_enabled)

    def load(self):
        self.__prefix_records = {}
        _conda_meta_dir = join(self.prefix_path, 'conda-meta')
        if lexists(_conda_meta_dir):
            for meta_file in fnmatch_filter(listdir(_conda_meta_dir), '*.json'):
                self._load_single_record(join(_conda_meta_dir, meta_file))
        if self._pip_interop_enabled:
            self._load_site_packages()

    def reload(self):
        self.load()
        return self

    def insert(self, prefix_record):
        assert prefix_record.name not in self._prefix_records

        assert prefix_record.fn.endswith(CONDA_TARBALL_EXTENSION)
        filename = prefix_record.fn[:-len(CONDA_TARBALL_EXTENSION)] + '.json'

        prefix_record_json_path = join(self.prefix_path, 'conda-meta', filename)
        if lexists(prefix_record_json_path):
            maybe_raise(BasicClobberError(
                source_path=None,
                target_path=prefix_record_json_path,
                context=context,
            ), context)
            rm_rf(prefix_record_json_path)

        write_as_json_to_file(prefix_record_json_path, prefix_record)

        self._prefix_records[prefix_record.name] = prefix_record

    def remove(self, package_name):
        assert package_name in self._prefix_records

        prefix_record = self._prefix_records[package_name]

        filename = prefix_record.fn[:-len(CONDA_TARBALL_EXTENSION)] + '.json'
        conda_meta_full_path = join(self.prefix_path, 'conda-meta', filename)
        if self.is_writable:
            rm_rf(conda_meta_full_path)

        del self._prefix_records[package_name]

    def get(self, package_name, default=NULL):
        try:
            return self._prefix_records[package_name]
        except KeyError:
            if default is not NULL:
                return default
            else:
                raise

    def iter_records(self):
        return itervalues(self._prefix_records)

    def iter_records_sorted(self):
        prefix_graph = PrefixGraph(self.iter_records())
        return iter(prefix_graph.graph)

    def all_subdir_urls(self):
        subdir_urls = set()
        for prefix_record in itervalues(self._prefix_records):
            subdir_url = prefix_record.channel.subdir_url
            if subdir_url and subdir_url not in subdir_urls:
                log.debug("adding subdir url %s for %s", subdir_url, prefix_record)
                subdir_urls.add(subdir_url)
        return subdir_urls

    def query(self, package_ref_or_match_spec):
        # returns a generator
        param = package_ref_or_match_spec
        if isinstance(param, string_types):
            param = MatchSpec(param)
        if isinstance(param, MatchSpec):
            return (prefix_rec for prefix_rec in self.iter_records()
                    if param.match(prefix_rec))
        else:
            assert isinstance(param, PackageRecord)
            return (prefix_rec for prefix_rec in self.iter_records() if prefix_rec == param)

    @property
    def _prefix_records(self):
        return self.__prefix_records or self.load() or self.__prefix_records

    def _load_single_record(self, prefix_record_json_path):
        log.trace("loading prefix record %s", prefix_record_json_path)
        with open(prefix_record_json_path) as fh:
            try:
                json_data = json_load(fh.read())
            except JSONDecodeError:
                raise CorruptedEnvironmentError(self.prefix_path, prefix_record_json_path)

            # TODO: consider, at least in memory, storing prefix_record_json_path as part
            #       of PrefixRecord
            prefix_record = PrefixRecord(**json_data)

            # check that prefix record json filename conforms to name-version-build
            # apparently implemented as part of #2638 to resolve #2599
            try:
                n, v, b = basename(prefix_record_json_path)[:-5].rsplit('-', 2)
                if (n, v, b) != (prefix_record.name, prefix_record.version, prefix_record.build):
                    raise ValueError()
            except ValueError:
                log.warn("Ignoring malformed prefix record at: %s", prefix_record_json_path)
                # TODO: consider just deleting here this record file in the future
                return

            self.__prefix_records[prefix_record.name] = prefix_record

    @property
    def is_writable(self):
        if self.__is_writable == NULL:
            test_path = join(self.prefix_path, PREFIX_MAGIC_FILE)
            if not isfile(test_path):
                is_writable = None
            else:
                is_writable = file_path_is_writable(test_path)
            self.__is_writable = is_writable
        return self.__is_writable

    # # REMOVE: ?
    def _has_python(self):
        return 'python' in self._prefix_records

    @property
    def _python_pkg_record(self):
        """Return the prefix record for the package python."""
        return next(
            (prefix_record for prefix_record in itervalues(self.__prefix_records)
             if prefix_record.name == 'python'),
            None
        )

    def _load_site_packages(self):
        """
        Load non-conda-installed python packages in the site-packages of the prefix.

        Python packages not handled by conda are installed via other means,
        like using pip or using python setup.py develop for local development.

        Packages found that are not handled by conda are converted into a
        prefix record and handled in memory.

        Packages clobbering conda packages (i.e. the conda-meta record) are
        removed from the in memory representation.
        """
        python_pkg_record = self._python_pkg_record

        if not python_pkg_record:
            return {}

        site_packages_dir = get_python_site_packages_short_path(python_pkg_record.version)
        site_packages_path = join(self.prefix_path, win_path_ok(site_packages_dir))

        if not isdir(site_packages_path):
            return {}

        # Get anchor files for corresponding conda (handled) python packages
        prefix_graph = PrefixGraph(self.iter_records())
        python_records = prefix_graph.all_descendants(python_pkg_record)
        conda_python_packages = get_conda_anchor_files_and_records(python_records)

        # Get all anchor files and compare against conda anchor files to find clobbered conda
        # packages and python packages installed via other means (not handled by conda)
        sp_anchor_files = get_site_packages_anchor_files(site_packages_path, site_packages_dir)
        conda_anchor_files = set(conda_python_packages)
        clobbered_conda_anchor_files = conda_anchor_files - sp_anchor_files
        non_conda_anchor_files = sp_anchor_files - conda_anchor_files

        # If there's a mismatch for anchor files between what conda expects for a package
        # based on conda-meta, and for what is actually in site-packages, then we'll delete
        # the in-memory record for the conda package.  In the future, we should consider
        # also deleting the record on disk in the conda-meta/ directory.
        for conda_anchor_file in clobbered_conda_anchor_files:
            del self._prefix_records[conda_python_packages[conda_anchor_file].name]

        # Create prefix records for python packages not handled by conda
        new_packages = {}
        python_records = get_python_records(non_conda_anchor_files, self.prefix_path,
                                            python_pkg_record.version)
        for python_record in python_records:
            self.__prefix_records[python_record.name] = python_record
            new_packages[python_record.name] = python_record

        return new_packages


def get_python_version_for_prefix(prefix):
    # returns a string e.g. "2.7", "3.4", "3.5" or None
    py_record_iter = (rcrd for rcrd in PrefixData(prefix).iter_records() if rcrd.name == 'python')
    record = next(py_record_iter, None)
    if record is None:
        return None
    next_record = next(py_record_iter, None)
    if next_record is not None:
        raise CondaDependencyError("multiple python records found in prefix %s" % prefix)
    else:
        return record.version[:3]


def delete_prefix_from_linked_data(path):
    '''Here, path may be a complete prefix or a dist inside a prefix'''
    linked_data_path = next((key for key in sorted(PrefixData._cache_, reverse=True)
                             if path.startswith(key)),
                            None)
    if linked_data_path:
        del PrefixData._cache_[linked_data_path]
        return True
    return False
