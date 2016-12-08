# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os import listdir
from os.path import basename, isdir, isfile, islink, join

from .path_actions import CacheUrlAction, ExtractPackageAction
from .. import CondaError
from .._vendor.auxlib.collection import first
from ..base.constants import CONDA_TARBALL_EXTENSION, DEFAULTS
from ..base.context import context
from ..common.compat import iteritems, iterkeys, with_metaclass
from ..common.url import join_url, path_to_url
from ..gateways.disk.test import try_write
from ..models.channel import Channel
from ..models.dist import Dist
from ..utils import md5_file

try:
    from cytoolz.itertoolz import concat, concatv, remove
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv, remove  # NOQA


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
        return first(self, lambda url: url.endswith(package_path))


class PackageCacheEntry(object):

    @classmethod
    def make_legacy(cls, pkgs_dir, channel):
        # the channel object here should be created using a full url to the tarball
        channel = Channel(channel)
        extracted_package_dir = join(pkgs_dir, Dist(channel).dist_name)
        package_tarball_full_path = extracted_package_dir + CONDA_TARBALL_EXTENSION
        return cls(pkgs_dir, channel, package_tarball_full_path, extracted_package_dir)

    def __init__(self, pkgs_dir, channel, package_tarball_full_path, extracted_package_dir):
        # the channel object here should be created using a full url to the tarball
        self.pkgs_dir = pkgs_dir
        self.channel = channel
        self.package_tarball_full_path = package_tarball_full_path
        self.extracted_package_dir = extracted_package_dir
        self.dist = Dist(channel)

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
        return self.is_fetched and md5_file(self.package_tarball_full_path) == md5sum

    @property
    def package_cache_writable(self):
        return PackageCache(self.pkgs_dir).is_writable


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

    @property
    def is_writable(self):
        # lazy and cached
        if self._is_writable is None:
            self._is_writable = try_write(self.pkgs_dir)
        return self._is_writable

    @classmethod
    def first_writable(cls, pkgs_dirs=None):
        if pkgs_dirs is None:
            pkgs_dirs = context.pkgs_dirs
        _first_writable = first((PackageCache(pd) for pd in pkgs_dirs),
                                key=lambda x: x.is_writable)
        if _first_writable is None:
            # TODO: raise NoWritablePackageCacheError()
            raise CondaError("No writable package cache directories found in\n"
                             "%s" % context.pkgs_dirs)
        return _first_writable

    @classmethod
    def get_matching_entries(cls, dist):
        return tuple(pc_entry
                     for pc_entry in (cls(pkgs_dir).get(dist)
                                      for pkgs_dir in context.pkgs_dirs)
                     if pc_entry)

    @classmethod
    def get_entry_to_link(cls, dist):
        pc_entry = next((pc_entry
                         for pc_entry in cls.get_matching_entries(dist)
                         if pc_entry.is_extracted),
                        None)
        if pc_entry is None:
            raise CondaError("No package '%s' found in cache directories.")
        return pc_entry

    def __getitem__(self, dist):
        return self._packages_map[dist]

    def __setitem__(self, dist, package_cache_entry):
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
        return iteritems(self._packages_map)

    def items(self):
        return self.iteritems()

    def __init__(self, pkgs_dir):
        self._packages_map = {}
        self._is_writable = None  # caching object for is_writable property

        self.pkgs_dir = pkgs_dir
        self.urls_data = UrlsData(pkgs_dir)
        self._init_dir()

    @property
    def cache_directory(self):
        return self.pkgs_dir

    def _init_dir(self):
        pkgs_dir = self.pkgs_dir
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
        channel = first(self.urls_data, lambda x: x.endswith(package_filename), DEFAULTS, Channel)
        pc_entry = PackageCacheEntry.make_legacy(pkgs_dir, channel)
        self._packages_map[pc_entry.dist] = pc_entry

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


def package_cache():
    log.warn('package_cache() is a no-op and deprecated')
    return {}


def cached_url(url):
    raise NotImplementedError()


def find_new_location(dist):
    """
    Determines the download location for the given package, and the name
    of a package, if any, that must be removed to make room. If the
    given package is already in the cache, it returns its current location,
    under the assumption that it will be overwritten. If the conflict
    value is None, that means there is no other package with that same
    name present in the cache (e.g., no collision).
    """
    raise NotImplementedError()


def is_fetched(dist):
    """
    Returns the full path of the fetched package, or None if it is not in the cache.
    """
    raise NotImplementedError()


def rm_fetched(dist):
    """
    Checks to see if the requested package is in the cache; and if so, it removes both
    the package itself and its extracted contents.
    """
    raise NotImplementedError()


def extracted():
    """
    return the (set of canonical names) of all extracted packages
    """


def is_extracted(dist):
    """
    returns the full path of the extracted data for the requested package,
    or None if that package is not extracted.
    """
    raise NotImplementedError()


def rm_extracted(dist):
    """
    Removes any extracted versions of the given package found in the cache.
    """
    raise NotImplementedError()


def extract(dist):
    """
    Extract a package, i.e. make a package available for linkage. We assume
    that the compressed package is located in the packages directory.
    """
    raise NotImplementedError()


# ##############################
# downloading
# ##############################


class ProgressiveFetchExtract(object):

    @staticmethod
    def make_actions_for_dist(dist, record):
        # returns a cache_action and extract_action

        package_cache_entries = PackageCache.get_matching_entries(dist)

        # look in the package cache for a matching dist that's already extracted
        # NOTE: next we check the md5 sum of a tarball, but we're not checking that here,
        #       so this could potentially give us a stale package
        # if a matching extracted package exists, there's nothing to do here
        first_extracted_pc_entry = next((pc_entry
                                         for pc_entry in package_cache_entries
                                         if pc_entry.is_extracted),
                                        None)
        if first_extracted_pc_entry is not None:
            return None, None

        # look for a downloaded tarball with an md5 match
        # if we can find a tarball on disk, extract it in place if that cache directory
        #   is writable
        # I'm struggling right now on whether we should use create_hard_link_or_copy() for
        #   the tarball if it's not in a writable cache directory.  The alternative is to
        #   leave the tarball where it is, extracting it to the first writable pkgs_dir,
        #   but without hardlinking/copying the tarball itself.  For 4.3 I think I'll
        #   default to hardlinking/copying; it seems safer for now.  If users present
        #   use cases where this isn't preferred, we can scale it back later or provide
        #   a config option.

        # filter out package_cache_entries with md5sums that don't match
        package_cache_entries = tuple(pc_entry for pc_entry in package_cache_entries
                                      if pc_entry.tarball_matches_md5(record['md5']))

        first_writable_pc_entry = next((pc_entry
                                        for pc_entry in package_cache_entries
                                        if pc_entry.package_cache_writable),
                                       None)
        if first_writable_pc_entry is not None:
            # we found a tarball, and it's in a writable package cache
            # extract the tarball in place
            extract_axn = ExtractPackageAction(
                source_full_path=first_writable_pc_entry.package_tarball_full_path,
                target_full_path=first_writable_pc_entry.extracted_package_dir,
            )
            return None, extract_axn

        if package_cache_entries:
            # we found a tarball, but it's not in a writable package cache
            # we need to link the tarball into the writable package cache,
            #   and then extract
            pc_entry = package_cache_entries[0]
            target_cache_directory = PackageCache.first_writable()
            cache_axn = CacheUrlAction(
                url=path_to_url(pc_entry.package_tarball_full_path),
                target_cache_directory=target_cache_directory,
                target_package_basename=dist.to_filename(),
                md5sum=record['md5'],
            )
            extract_axn = ExtractPackageAction(
                source_full_path=cache_axn.target_full_path,
                target_full_path=pc_entry.extracted_package_dir,
            )
            return cache_axn, extract_axn

        # if we got here, no matching extracted directory or tarball was found
        # there is no matching package_cache_entry
        # we need to fetch, and then extract
        url = record.get('url') or join_url(record.channel, record.fn)
        channel = Channel(url)
        target_cache_directory = PackageCache.first_writable().cache_directory

        cache_axn = CacheUrlAction(
            url=channel.url(),
            target_cache_directory=target_cache_directory,
            target_package_basename=dist.to_filename(),
            md5sum=record['md5'],
        )
        extract_axn = ExtractPackageAction(
            source_full_path=cache_axn.target_full_path,
            target_full_path=cache_axn.target_full_path[:-len(CONDA_TARBALL_EXTENSION)],
        )
        return cache_axn, extract_axn

    def __init__(self, index, link_dists):
        self.index = index
        self.link_dists = link_dists

        self._prepared = False
        self._verified = False

    def prepare(self):
        if self._prepared:
            return

        cache_actions, extract_actions = zip(*(self.make_actions_for_dist(dist, self.index[dist])
                                             for dist in self.link_dists))
        self.cache_actions = tuple(ca for ca in cache_actions if ca)
        self.extract_actions = tuple(ea for ea in extract_actions if ea)
        self._prepared = True

    def verify(self):
        if not self._prepared:
            self.prepare()
        for axn in concatv(self.cache_actions, self.extract_actions):
            axn.verify()
        self._verified = True

    def execute(self):
        if not self._verified:
            self.verify()

        for action in concatv(self.cache_actions, self.extract_actions):
            try:
                self._execute_action(action)
            finally:
                action.cleanup()

    @staticmethod
    def _execute_action(action):
        max_tries = 3
        exceptions = []
        for q in range(max_tries):
            try:
                action.execute()
            except Exception as e:
                action.reverse()
                exceptions.append(e)
            else:
                return
        # TODO: this exception stuff here needs work
        raise CondaError('\n'.join(exceptions))


def fetch_pkg(info, package_tarball_full_path, session=None):
    '''
    fetch a package given by `info` and store it into `dst_dir`
    '''
    raise NotImplementedError()


def download(url, dst_path, session=None, md5=None, urlstxt=False, retries=3):
    raise NotImplementedError()
