# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os import listdir
from os.path import basename, isdir, isfile, islink, join
from traceback import format_exc

from .path_actions import CacheUrlAction, ExtractPackageAction
from .. import CondaError, CondaMultiError
from .._vendor.auxlib.collection import first
from .._vendor.auxlib.decorators import memoizemethod
from .._vendor.auxlib.path import expand
from ..base.constants import CONDA_TARBALL_EXTENSION, UNKNOWN_CHANNEL
from ..base.context import context
from ..common.compat import iteritems, iterkeys, itervalues, text_type, with_metaclass
from ..common.path import safe_basename, url_to_path
from ..common.url import path_to_url
from ..gateways.disk.create import create_package_cache_directory
from ..gateways.disk.read import compute_md5sum
from ..gateways.disk.test import file_path_is_writable
from ..models.channel import Channel
from ..models.dist import Dist
from ..utils import md5_file

try:
    from cytoolz.itertoolz import concat, concatv, groupby, remove
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv, groupby, remove  # NOQA


log = getLogger(__name__)
stderrlog = getLogger('stderrlog')


class UrlsData(object):
    # this is a class to manage urls.txt
    # it should basically be thought of as a sequence
    # in this class I'm breaking the rule that all disk access goes through conda.gateways

    def __init__(self, pkgs_dir):
        self.pkgs_dir = pkgs_dir
        self.urls_txt_path = urls_txt_path = join(pkgs_dir, 'urls.txt')
        if isfile(urls_txt_path):
            with open(urls_txt_path, 'r') as fh:
                self._urls_data = [line.strip() for line in fh]
                self._urls_data.reverse()
        else:
            self._urls_data = []

    def __contains__(self, url):
        return url in self._urls_data

    def __iter__(self):
        return iter(self._urls_data)

    def add_url(self, url):
        with open(self.urls_txt_path, 'a') as fh:
            fh.write(url + '\n')
        self._urls_data.insert(0, url)

    def get_url(self, package_path):
        # package path can be a full path or just a basename
        #   can be either an extracted directory or tarball
        package_path = basename(package_path)
        if not package_path.endswith(CONDA_TARBALL_EXTENSION):
            package_path += CONDA_TARBALL_EXTENSION
        return first(self, lambda url: safe_basename(url) == package_path)


class PackageCacheEntry(object):

    @classmethod
    def make_legacy(cls, pkgs_dir, dist):
        # the dist object here should be created using a full url to the tarball
        extracted_package_dir = join(pkgs_dir, dist.dist_name)
        package_tarball_full_path = extracted_package_dir + CONDA_TARBALL_EXTENSION
        return cls(pkgs_dir, dist, package_tarball_full_path, extracted_package_dir)

    def __init__(self, pkgs_dir, dist, package_tarball_full_path, extracted_package_dir):
        # the channel object here should be created using a full url to the tarball
        self.pkgs_dir = pkgs_dir
        self.dist = dist
        self.package_tarball_full_path = package_tarball_full_path
        self.extracted_package_dir = extracted_package_dir
        self.channel = Channel(dist.to_url()) if dist.is_channel else Channel(None)

    @property
    def is_fetched(self):
        return isfile(self.package_tarball_full_path)

    @property
    def is_extracted(self):
        return isdir(self.extracted_package_dir)

    @property
    def tarball_basename(self):
        return basename(self.package_tarball_full_path)

    def tarball_matches_md5(self, md5sum):
        return self.md5sum == md5sum

    def tarball_matches_md5_if(self, md5sum):
        return not md5sum or self.md5sum == md5sum

    @property
    def package_cache_writable(self):
        return PackageCache(self.pkgs_dir).is_writable

    @property
    def md5sum(self):
        return self._calculate_md5sum() if self.is_fetched else None

    def get_urls_txt_value(self):
        return PackageCache(self.pkgs_dir).urls_data.get_url(self.package_tarball_full_path)

    @memoizemethod
    def _calculate_md5sum(self):
        assert self.is_fetched
        return md5_file(self.package_tarball_full_path)

    def __repr__(self):
        args = ('%s=%r' % (key, getattr(self, key))
                for key in ('dist', 'package_tarball_full_path'))
        return "%s(%s)" % (self.__class__.__name__, ', '.join(args))


class PackageCacheType(type):
    """
    This metaclass does basic caching of PackageCache instance objects.
    """

    def __call__(cls, pkgs_dir):
        if isinstance(pkgs_dir, PackageCache):
            return pkgs_dir
        elif pkgs_dir in PackageCache._cache_:
            return PackageCache._cache_[pkgs_dir]
        else:
            package_cache_instance = super(PackageCacheType, cls).__call__(pkgs_dir)
            PackageCache._cache_[pkgs_dir] = package_cache_instance
            return package_cache_instance

    def __getitem__(cls, dist):
        return cls.get_entry_to_link(dist)


@with_metaclass(PackageCacheType)
class PackageCache(object):
    _cache_ = {}

    def __init__(self, pkgs_dir):
        self._packages_map = {}
        # type: Dict[Dist, PackageCacheEntry]

        self.pkgs_dir = pkgs_dir
        self.urls_data = UrlsData(pkgs_dir)

        # caching object for is_writable property
        self._is_writable = None

        self._init_dir()

    # ##########################################################################################
    # these class methods reach across all package cache directories (usually context.pkgs_dirs)
    # ##########################################################################################

    @classmethod
    def first_writable(cls, pkgs_dirs=None):
        return cls.all_writable(pkgs_dirs)[0]

    @classmethod
    def all_writable(cls, pkgs_dirs=None):
        if pkgs_dirs is None:
            pkgs_dirs = context.pkgs_dirs
        writable_caches = tuple(filter(lambda c: c.is_writable,
                                       (PackageCache(pd) for pd in pkgs_dirs)))
        if not writable_caches:
            # TODO: raise NoWritablePackageCacheError()
            raise CondaError("No writable package cache directories found in\n"
                             "%s" % text_type(context.pkgs_dirs))
        return writable_caches

    @classmethod
    def read_only_caches(cls, pkgs_dirs=None):
        if pkgs_dirs is None:
            pkgs_dirs = context.pkgs_dirs
        read_only_caches = tuple(filter(lambda c: not c.is_writable,
                                        (PackageCache(pd) for pd in pkgs_dirs)))
        return read_only_caches

    @classmethod
    def get_all_extracted_entries(cls):
        package_caches = (PackageCache(pd) for pd in context.pkgs_dirs)
        return tuple(pc_entry for pc_entry in concat(map(itervalues, package_caches))
                     if pc_entry.is_extracted)

    @classmethod
    def get_matching_entries(cls, dist):
        matches = tuple(pc_entry
                        for pc_entry in (cls(pkgs_dir).get(dist)
                                         for pkgs_dir in context.pkgs_dirs)
                        if pc_entry)
        return matches

    @classmethod
    def get_entry_to_link(cls, dist):
        pc_entry = next((pc_entry
                         for pc_entry in cls.get_matching_entries(dist)
                         if pc_entry.is_extracted),
                        None)
        if pc_entry is not None:
            return pc_entry

        # this can happen with `conda install path/to/package.tar.bz2`
        #   because dist has channel '<unknown>'
        # if ProgressiveFetchExtract did it's job correctly, what we're looking for
        #   should be the matching dist_name in the first writable package cache
        # we'll search all caches for a match, but search writable caches first
        grouped_caches = groupby(lambda x: x.is_writable,
                                 (PackageCache(pd) for pd in context.pkgs_dirs))
        caches = concatv(grouped_caches.get(True, ()), grouped_caches.get(False, ()))
        pc_entry = next((cache.scan_for_dist_no_channel(dist) for cache in caches if cache), None)
        if pc_entry is not None:
            return pc_entry
        raise CondaError("No package '%s' found in cache directories." % dist)

    def scan_for_dist_no_channel(self, dist):
        # type: (Dist) -> PackageCacheEntry
        return next((pc_entry for this_dist, pc_entry in iteritems(self)
                     if this_dist.dist_name == dist.dist_name),
                    None)

    @classmethod
    def tarball_file_in_cache(cls, tarball_path, md5sum=None):
        tarball_full_path, md5sum = cls._clean_tarball_path_and_get_md5sum(tarball_path, md5sum)
        pc_entry = first(PackageCache(pkgs_dir).tarball_file_in_this_cache(tarball_full_path,
                                                                           md5sum)
                         for pkgs_dir in context.pkgs_dirs)
        return pc_entry

    @classmethod
    def clear(cls):
        cls._cache_.clear()

    def tarball_file_in_this_cache(self, tarball_path, md5sum=None):
        tarball_full_path, md5sum = self._clean_tarball_path_and_get_md5sum(tarball_path,
                                                                            md5sum=md5sum)
        tarball_basename = basename(tarball_full_path)
        pc_entry = first((pc_entry for pc_entry in itervalues(self)),
                         key=lambda pce: pce.tarball_basename == tarball_basename
                                         and pce.tarball_matches_md5(md5sum))  # NOQA
        return pc_entry

    def _init_dir(self):
        pkgs_dir = self.pkgs_dir
        if not isdir(pkgs_dir):
            return
        pkgs_dir_contents = listdir(pkgs_dir)
        while pkgs_dir_contents:
            base_name = pkgs_dir_contents.pop(0)
            full_path = join(pkgs_dir, base_name)
            if islink(full_path):
                continue
            elif isdir(full_path) and isfile(join(full_path, 'info', 'index.json')):
                package_filename = base_name + CONDA_TARBALL_EXTENSION
                self._add_entry(pkgs_dir, package_filename)
                self._remove_match(pkgs_dir_contents, base_name)
            elif isfile(full_path) and full_path.endswith(CONDA_TARBALL_EXTENSION):
                package_filename = base_name
                self._add_entry(pkgs_dir, package_filename)
                self._remove_match(pkgs_dir_contents, base_name)

    def _add_entry(self, pkgs_dir, package_filename):
        dist = first(self.urls_data, lambda x: safe_basename(x) == package_filename, apply=Dist)
        if not dist:
            dist = Dist.from_string(package_filename, channel_override=UNKNOWN_CHANNEL)
        pc_entry = PackageCacheEntry.make_legacy(pkgs_dir, dist)
        self._packages_map[pc_entry.dist] = pc_entry

    @property
    def cache_directory(self):
        return self.pkgs_dir

    @property
    def is_writable(self):
        # lazy and cached
        # This method takes the action of creating an empty package cache if it does not exist.
        #   Logic elsewhere, both in conda and in code that depends on conda, seems to make that
        #   assumption.
        if self._is_writable is None:
            if isdir(self.pkgs_dir):
                self._is_writable = file_path_is_writable(self.urls_data.urls_txt_path)
            else:
                log.debug("package cache directory '%s' does not exist", self.pkgs_dir)
                self._is_writable = create_package_cache_directory(self.pkgs_dir)
        return self._is_writable

    @staticmethod
    def _remove_match(pkg_dir_contents, base_name):
        # pop and return the matching tarball or directory to base_name
        #   if not match, return None
        try:
            pkg_dir_contents.remove(base_name[:-len(CONDA_TARBALL_EXTENSION)]
                                    if base_name.endswith(CONDA_TARBALL_EXTENSION)
                                    else base_name + CONDA_TARBALL_EXTENSION)
        except ValueError:
            pass

    @staticmethod
    def _clean_tarball_path_and_get_md5sum(tarball_path, md5sum=None):
        if tarball_path.startswith('file:/'):
            tarball_path = url_to_path(tarball_path)
        tarball_full_path = expand(tarball_path)

        if isfile(tarball_full_path) and md5sum is None:
            md5sum = compute_md5sum(tarball_full_path)

        return tarball_full_path, md5sum

    def __getitem__(self, dist):
        return self._packages_map[dist]

    def __setitem__(self, dist, package_cache_entry):
        # TODO: should this method also write to urls.txt?
        # I'm not sure. Currently, additions to urls.txt are decoupled from additions to package
        #   cache via CacheUrlAction and ExtractPackageAction
        self._packages_map[dist] = package_cache_entry

    def __delitem__(self, dist):
        del self._packages_map[dist]

    def get(self, dist, default=None):
        return self._packages_map.get(dist, default)

    def __contains__(self, dist):
        return dist in self._packages_map

    def __iter__(self):
        return iterkeys(self._packages_map)

    def iteritems(self):
        return iter(self.items())

    def items(self):
        return self._packages_map.items()

    def itervalues(self):
        return iter(self.values())

    def values(self):
        return self._packages_map.values()

    def __repr__(self):
        args = ('%s=%r' % (key, getattr(self, key)) for key in ('pkgs_dir',))
        return "%s(%s)" % (self.__class__.__name__, ', '.join(args))


# ##############################
# downloading
# ##############################

class ProgressiveFetchExtract(object):

    @staticmethod
    def make_actions_for_dist(dist, record):
        assert record is not None, dist
        # returns a cache_action and extract_action

        # look in all caches for a dist that's already extracted and matches
        # the MD5 if one has been supplied. if one exists, no action needed.
        md5 = record.get('md5')
        extracted_pc_entry = first(
            (PackageCache(pkgs_dir).get(dist) for pkgs_dir in context.pkgs_dirs),
            key=lambda pce: pce and pce.is_extracted and pce.tarball_matches_md5_if(md5)
        )
        if extracted_pc_entry:
            return None, None

        # there is no extracted dist that can work, so now we look for tarballs that
        #   aren't extracted
        # first we look in all writable caches, and if we find a match, we extract in place
        # otherwise, if we find a match in a non-writable cache, we link it to the first writable
        #   cache, and then extract
        first_writable_cache = PackageCache.first_writable()
        pc_entry_writable_cache = first(
            (writable_cache.get(dist) for writable_cache in PackageCache.all_writable()),
            key=lambda pce: pce and pce.is_fetched and pce.tarball_matches_md5_if(md5)
        )
        if pc_entry_writable_cache:
            # extract in place
            extract_axn = ExtractPackageAction(
                source_full_path=pc_entry_writable_cache.package_tarball_full_path,
                target_pkgs_dir=pc_entry_writable_cache.pkgs_dir,
                target_extracted_dirname=pc_entry_writable_cache.dist.dist_name,
            )
            return None, extract_axn

        pc_entry_read_only_cache = first(
            (pce_read_only.get(dist) for pce_read_only in PackageCache.read_only_caches()),
            key=lambda pce: pce and pce.is_fetched and pce.tarball_matches_md5_if(md5)
        )
        if pc_entry_read_only_cache:
            # we found a tarball, but it's in a read-only package cache
            # we need to link the tarball into the first writable package cache,
            #   and then extract
            cache_axn = CacheUrlAction(
                url=path_to_url(pc_entry_read_only_cache.package_tarball_full_path),
                target_pkgs_dir=first_writable_cache.pkgs_dir,
                target_package_basename=dist.to_filename(),
                md5sum=md5,
            )
            extract_axn = ExtractPackageAction(
                source_full_path=cache_axn.target_full_path,
                target_pkgs_dir=first_writable_cache.pkgs_dir,
                target_extracted_dirname=dist.dist_name,
            )
            return cache_axn, extract_axn

        # if we got here, we couldn't find a matching package in the caches
        #   we'll have to download one; fetch and extract
        cache_axn = CacheUrlAction(
            url=record.get('url') or dist.to_url(),
            target_pkgs_dir=first_writable_cache.pkgs_dir,
            target_package_basename=dist.to_filename(),
            md5sum=md5,
        )
        extract_axn = ExtractPackageAction(
            source_full_path=cache_axn.target_full_path,
            target_pkgs_dir=first_writable_cache.pkgs_dir,
            target_extracted_dirname=dist.dist_name,
        )
        return cache_axn, extract_axn

    def __init__(self, index, link_dists):
        self.index = index
        self.link_dists = link_dists

        log.debug("instantiating ProgressiveFetchExtract with\n"
                  "  %s\n", '\n  '.join(text_type(dist) for dist in link_dists))

        self.cache_actions = ()
        self.extract_actions = ()

        self._prepared = False

    def prepare(self):
        if self._prepared:
            return

        paired_actions = tuple(self.make_actions_for_dist(dist, self.index[dist])
                               for dist in self.link_dists)
        if len(paired_actions) > 0:
            cache_actions, extract_actions = zip(*paired_actions)
            self.cache_actions = tuple(ca for ca in cache_actions if ca)
            self.extract_actions = tuple(ea for ea in extract_actions if ea)
        else:
            self.cache_actions = self.extract_actions = ()

        log.debug("prepared package cache actions:\n"
                  "  cache_actions:\n"
                  "    %s\n"
                  "  extract_actions:\n"
                  "    %s\n",
                  '\n    '.join(text_type(ca) for ca in self.cache_actions),
                  '\n    '.join(text_type(ea) for ea in self.extract_actions))

        self._prepared = True

    def execute(self):
        if not self._prepared:
            self.prepare()

        for action in concatv(self.cache_actions, self.extract_actions):
            self._execute_action(action)

    @staticmethod
    def _execute_action(action):
        if not action.verified:
            action.verify()

        max_tries = 3
        exceptions = []
        for q in range(max_tries):
            try:
                action.execute()
            except Exception as e:
                log.debug("Error in action %s", action)
                log.debug(format_exc())
                action.reverse()
                exceptions.append(CondaError(repr(e)))
            else:
                action.cleanup()
                return

        # TODO: this exception stuff here needs work
        raise CondaMultiError(exceptions)

    def __hash__(self):
        return hash(self.link_dists)

    def __eq__(self, other):
        return hash(self) == hash(other)


# ##############################
# backward compatibility
# ##############################

def rm_fetched(dist):
    """
    Checks to see if the requested package is in the cache; and if so, it removes both
    the package itself and its extracted contents.
    """
    # in conda/exports.py and conda_build/conda_interface.py, but not actually
    #   used in conda-build
    raise NotImplementedError()


def download(url, dst_path, session=None, md5=None, urlstxt=False, retries=3):
    from ..gateways.download import download as gateway_download
    gateway_download(url, dst_path, md5)


class package_cache(object):

    def __contains__(self, dist):
        return dist in PackageCache.first_writable()

    def keys(self):
        return iter(PackageCache.first_writable())

    def __delitem__(self, dist):
        del PackageCache.first_writable()[dist]
