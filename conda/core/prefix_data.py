# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
from logging import getLogger
from os import listdir
from os.path import basename, isfile, join, lexists

from ..base.constants import CONDA_TARBALL_EXTENSION, PREFIX_MAGIC_FILE
from ..base.context import context
from ..common.compat import JSONDecodeError, itervalues, string_types, with_metaclass
from ..common.constants import NULL
from ..common.path import get_python_site_packages_short_path, win_path_ok
from ..common.serialize import json_load
from ..exceptions import (BasicClobberError, CondaDependencyError, CorruptedEnvironmentError,
                          maybe_raise)
from ..gateways.disk.create import write_as_json_to_file
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.test import file_path_is_writable
from ..models.channel import Channel
from ..models.dist import Dist
from ..models.enums import PackageType, PathType
from ..models.match_spec import MatchSpec
from ..models.prefix_graph import PrefixGraph
from ..models.records import (ComposableField, EnumField, ListField, PackageRef, PathDataV1,
                              PathsData, PrefixRecord)

try:
    from cytoolz.itertoolz import concat, concatv
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concat, concatv  # NOQA


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

    def _has_python(self):
        return 'python' in self._prefix_records

    def _load_site_packages(self):
        # 1. identify all package names in site-packages
        # 2. determine if they are conda packages
        # 3. load as pip packages if not
        python_record = next(
            (prefix_rec for prefix_rec in itervalues(self.__prefix_records) if prefix_rec.name == 'python'),
            None
        )
        if not python_record:
            return
        prefix_graph = PrefixGraph(self.iter_records())
        known_python_records = prefix_graph.all_descendants(python_record)

        def norm_package_name(name):
            return name.replace('.', '-').replace('_', '-').lower()

        marker_file_endings = ('.egg-info/PKG-INFO', '.dist-info/RECORD', '.egg-info')
        conda_python_packages = dict(
            ((mf, prefix_rec)
             for prefix_rec in known_python_records
             for mf in prefix_rec.files
             if mf.endswith(marker_file_endings))
        )

        non_conda_python_package_markers = []
        site_packages_dir = get_python_site_packages_short_path(python_record.version)
        sp_dir_full_path = join(self.prefix_path, win_path_ok(site_packages_dir))
        sp_marker_endings = ('.dist-info', '.egg-info')
        for fn in listdir(sp_dir_full_path):
            if fn.endswith(sp_marker_endings):
                if fn.endswith('.dist-info'):
                    marker_file = "%s/%s/%s" % (site_packages_dir, fn, 'RECORD')
                elif fn.endswith(".egg-info"):
                    if isfile(join(sp_dir_full_path, fn)):
                        marker_file = "%s/%s" % (site_packages_dir, fn)
                    else:
                        marker_file = "%s/%s/%s" % (site_packages_dir, fn, "PKG-INFO")
                elif fn.endswith('.egg-link'):
                    continue
                elif fn.endswith('.pth'):
                    continue
                else:
                    continue

                if marker_file not in conda_python_packages:
                    non_conda_python_package_markers.append(marker_file)

        from pip._vendor.distlib.database import EggInfoDistribution, InstalledDistribution  # TODO: only compatible with pip 9.0
        from pip._vendor.distlib.metadata import MetadataConflictError
        from pip._vendor.distlib.util import parse_requirement

        def get_pydist(marker_file):
            if ".dist-info" in marker_file:
                dist_file = join(self.prefix_path, win_path_ok(marker_file.rsplit('/', 1)[0]))
                dist_cls = InstalledDistribution
            elif marker_file.endswith(".egg-info"):
                dist_file = join(self.prefix_path, win_path_ok(marker_file))
                dist_cls = EggInfoDistribution
            elif ".egg-info" in marker_file:
                dist_file = join(self.prefix_path, win_path_ok(marker_file.rsplit('/', 1)[0]))
                dist_cls = EggInfoDistribution
            else:
                raise NotImplementedError()
            try:
                pydist = dist_cls(dist_file)
            except MetadataConflictError:
                print("MetadataConflictError:", marker_file)
                pydist = None
            return pydist

        python_recs = []
        for marker_file in non_conda_python_package_markers:
            pydist = get_pydist(marker_file)
            if pydist is None:
                continue
            # x.provides  =>  [u'skdata (0.0.4)']
            # x.run_requires  =>  set([u'joblib', u'scikit-learn', u'lockfile', u'numpy', u'nose (>=1.0)'])
            # >>> list(x.list_installed_files())  =>  [(u'skdata/__init__.py', u'sha256=47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU', u'0'), (u'skdata/base.py', u'sha256=04MW02dky5T4nZb6Q0M351aRbAwLxd8voCK3nrAU-g0', u'5019'), (u'skdata/brodatz.py', u'sha256=NIPWLawJ59Fr037r0oT_gHe46WCo3UivuQ-cwxRU3ow', u'8492'), (u'skdata/caltech.py', u'sha256=cIfyMMRYggZ3Jkgc15tsYi_ZsZ7NpRqWh7mZ8bl6Fo0', u'8047'), (u'skdata/data_home.py', u'sha256=o5ChOI4v3Jd16JM3qWZlhrs5q-g_0yKa5-Oq44HC_K4', u'1297'), (u'skdata/diabetes.py', u'sha256=ny5Ihpc_eiIRYgzFn3Lm81fV0SZ1nyZQnqEmwb2PrS0', u'995'), (u'skdata/digits.py', u'sha256=DipeWAb3APpjXfmKmSumkfEFzuBW8XJ0

            # TODO: normalize names against '.', '-', '_'
            # TODO: ensure that this dist is *actually* the dist that matches conda-meta

            if marker_file.endswith(".egg-info"):
                paths_data = None
            else:
                _paths_data = []
                for _path, _hash, _size in pydist.list_installed_files():
                    if _hash:
                        assert _hash.startswith('sha256='), (marker_file, _hash)
                        sha256 = _hash[7:]
                    else:
                        sha256 = None
                    _size = int(_size) if _size else None
                    _paths_data.append(PathDataV1(
                        _path=_path,
                        path_type=PathType.hardlink,  # TODO
                        sha256=sha256,
                        size_in_bytes=_size
                    ))
                paths_data = PathsData(paths_version=1, paths=_paths_data)
            # TODO: need to add entry points, "exports," and other files that might not be in RECORD

            depends = tuple(
                req.name for req in
                # vars(req) => {'source': u'nose (>=1.0)', 'requirement': u'nose (>= 1.0)', 'extras': None, 'name': u'nose', 'url': None, 'constraints': [(u'>=', u'1.0')]}
                (parse_requirement(r) for r in pydist.run_requires)
            )
            # TODO: need to add python (with version?) to deps

            package_type = PackageType.SHADOW_PIP_UPDATEABLE if depends else PackageType.SHADOW_PIP_FROZEN

            python_rec = PythonRecord(
                package_type=PackageType.SHADOW_PIP_FROZEN,
                name=pydist.name.lower(),
                version=pydist.version,
                channel=Channel('pypi'),
                subdir='pypi',
                fn=basename(marker_file),
                build='pypi_0',
                build_number=0,
                paths_data=paths_data,
                depends=depends
            )
            python_recs.append(python_rec)
            self.__prefix_records[python_rec.name] = python_rec


class PythonRecord(PackageRef):

    depends = ListField(string_types, default=())
    paths_data = ComposableField(PathsData, required=False, nullable=True, default_in_dump=False)
    package_type = EnumField(PackageType, required=False, nullable=True)


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


if __name__ == '__main__':
    pd = PrefixData('/Users/kfranz/anaconda')
    pd._load_site_packages()
