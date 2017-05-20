# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
from logging import getLogger
from os.path import join, lexists, dirname, isdir

from conda.gateways.disk.create import mkdir_p

from ..base.constants import CONDA_TARBALL_EXTENSION
from ..base.context import context
from ..common.compat import itervalues, with_metaclass
from ..common.constants import NULL
from ..common.serialize import json_load
from ..exceptions import BasicClobberError, CondaDependencyError, maybe_raise
from ..gateways.disk.create import write_as_json_to_file
from ..gateways.disk.delete import rm_rf
from ..models.dist import Dist
from ..models.index_record import PrefixRecord
from ..models.match_spec import MatchSpec

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
        self._prefix_records = None

    def load(self):
        self._prefix_records = {}
        for meta_file in glob(join(self.prefix_path, 'conda-meta', '*.json')):
            self._load_single_record(meta_file)

    def insert(self, prefix_record):
        self._ensure_loaded()
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
        self._ensure_loaded()
        assert package_name in self._prefix_records

        prefix_record = self._prefix_records[package_name]

        filename = prefix_record.fn[:-len(CONDA_TARBALL_EXTENSION)] + '.json'
        conda_meta_full_path = join(self.prefix_path, 'conda-meta', filename)
        rm_rf(conda_meta_full_path)

        del self._prefix_records[package_name]

    def get(self, package_name, default=NULL):
        self._ensure_loaded()
        try:
            return self._prefix_records[package_name]
        except KeyError:
            if default is not NULL:
                return default
            else:
                raise



    def _ensure_loaded(self):
        if self._prefix_records is None:
            self.load()

    def _load_single_record(self, prefix_record_json_path):
        with open(prefix_record_json_path) as fh:
            json_data = json_load(fh.read())
        prefix_record = PrefixRecord(**json_data)
        self._prefix_records[prefix_record.name] = prefix_record



def get_python_version_for_prefix(prefix):
    # returns a string e.g. "2.7", "3.4", "3.5" or None
    pd = PrefixData(prefix)
    record = pd.get('python', None)
    py_record_iter = (rcrd for rcrd in itervalues(linked_data(prefix)) if rcrd.name == 'python')
    record = next(py_record_iter, None)
    if record is None:
        return None
    next_record = next(py_record_iter, None)
    if next_record is not None:
        raise CondaDependencyError("multiple python records found in prefix %s" % prefix)
    else:
        return record.version[:3]




# exports
def linked_data(prefix, ignore_channels=False):
    """
    Return a dictionary of the linked packages in prefix.
    """
    pd = PrefixData(prefix)
    pd._ensure_loaded()
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
    prefix_record = pd.get(dist.name)
    if MatchSpec(dist).match(prefix_record):
        return prefix_record
    else:
        return None
