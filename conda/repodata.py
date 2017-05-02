# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals
from .core import repodata as _impl
from .common.compat import with_metaclass
from .connection import CondaSession
from collections import OrderedDict
from os.path import join

class RepoDataType(type):
    """This (meta) class provides (ordered) dictionary-like access to Repodata."""

    def __init__(cls, name, bases, dict):
        cls._instances = OrderedDict()

    def __getitem__(cls, url):
        return cls._instances[url]

    def __iter__(cls):
        return iter(cls._instances)

    def __reversed__(cls):
        return reversed(cls._instances)

    def __len__(cls):
        return len(cls._instances)

@with_metaclass(RepoDataType)
class RepoData(object):
    """This object represents all the package metainfo of a single channel."""

    @staticmethod
    def enable(url, name, priority, cache_dir=None):
        RepoData._instances[url] = RepoData(url, name, priority, cache_dir)

    @staticmethod
    def get(url):
        return RepoData._instances.get(url)

    @staticmethod
    def clear():
        RepoData._instances.clear()

    @staticmethod
    def load_all(use_cache=False):
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(10) as e:
                for rd in RepoData._instances.values():
                    e.submit(rd.load(use_cache=use_cache, session=CondaSession()))
        except (ImportError) as e:
            for rd in RepoData._instances.values():
                rd.load(use_cache=use_cache, session=CondaSession())

    def __init__(self, url, name, priority, cache_dir=None):
        """Create a RepoData object."""

        self.url = url
        self.name = name
        self.priority = priority
        self.cache_dir = cache_dir
        self._data = None

    def load(self, use_cache=False, session=None):
        """Syncs this object with an upstream RepoData object."""

        session = session if session else CondaSession()
        self._data = _impl.fetch_repodata(self.url, self.name, self.priority,
                                          cache_dir=self.cache_dir,
                                          use_cache=use_cache, session=session)

    def _persist(self, cache_dir=None):
        """Save data to local cache."""

        cache_path = join(cache_dir or self.cache_dir or _impl.create_cache_dir(),
                          _impl.cache_fn_url(self.url))
        _impl.write_pickled_repodata(cache_path, self._data)

    def query(self, query):
        """query information about a package"""
        raise NotImplemented

    def contains(self, package_ref):
        """Check whether the package is contained in this channel."""
        raise NotImplemented

    def validate(self, package_ref):
        """Check whether the package could be added to this channel."""
        raise NotImplemented

    def add(self, package_ref):
        """Add the given package-ref to this channel."""
        raise NotImplemented

    def remove(self, package_ref):
        """Remove the given package-ref from this channel."""
        raise NotImplemented

    @property
    def index(self):
        # WARNING: This method will soon be deprecated.
        return self._data
