# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
from logging import getLogger
from os.path import isfile, join, lexists

from ..base.constants import CONDA_TARBALL_EXTENSION, PREFIX_MAGIC_FILE
from ..base.context import context
from ..common.compat import JSONDecodeError, itervalues, string_types, with_metaclass
from ..common.constants import NULL
from ..common.serialize import json_load
from ..exceptions import (BasicClobberError, CondaDependencyError, CorruptedEnvironmentError,
                          maybe_raise)
from ..gateways.disk.create import write_as_json_to_file
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.test import file_path_is_writable
from ..models.dist import Dist
from ..models.match_spec import MatchSpec
from ..models.records import PackageRef, PrefixRecord

log = getLogger(__name__)


class PrefixDataType(type):
    """Basic caching of PrefixData instance objects."""

    def __call__(cls, prefix_path):
        if prefix_path in PrefixData._cache_:
            return PrefixData._cache_[prefix_path]
        elif isinstance(prefix_path, PrefixData):
            return prefix_path
        else:
            prefix_data_instance = super(PrefixDataType, cls).__call__(prefix_path)
            PrefixData._cache_[prefix_path] = prefix_data_instance
            return prefix_data_instance


@with_metaclass(PrefixDataType)
class PrefixData(object):
    _cache_ = {}

    def __init__(self, prefix_path):
        self.prefix_path = prefix_path
        self.__prefix_records = None

    def load(self):
        self.__prefix_records = {}
        for meta_file in glob(join(self.prefix_path, 'conda-meta', '*.json')):
            self._load_single_record(meta_file)

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
        from ..resolve import Resolve
        index = {Dist(rec): rec for rec in self.iter_records()}
        r = Resolve(index)
        sorted_dists = r.dependency_sort({d.name: d for d in index})
        return (index[d] for d in sorted_dists)

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
            assert isinstance(param, PackageRef)
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

        prefix_record = PrefixRecord(**json_data)
        self.__prefix_records[prefix_record.name] = prefix_record

    @property
    def is_writable(self):
        test_path = join(self.prefix_path, PREFIX_MAGIC_FILE)
        if not isfile(test_path):
            return None
        return file_path_is_writable(test_path)


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


# exports
def linked_data(prefix, ignore_channels=False):
    """
    Return a dictionary of the linked packages in prefix.
    """
    pd = PrefixData(prefix)
    return {Dist(prefix_record): prefix_record for prefix_record in itervalues(pd._prefix_records)}


# exports
def linked(prefix, ignore_channels=False):
    """
    Return the set of canonical names of linked packages in prefix.
    """
    return set(linked_data(prefix, ignore_channels=ignore_channels).keys())


# exports
def is_linked(prefix, dist):
    """
    Return the install metadata for a linked package in a prefix, or None
    if the package is not linked in the prefix.
    """
    # FIXME Functions that begin with `is_` should return True/False
    pd = PrefixData(prefix)
    prefix_record = pd.get(dist.name, None)
    if prefix_record is None:
        return None
    elif MatchSpec(dist).match(prefix_record):
        return prefix_record
    else:
        return None
