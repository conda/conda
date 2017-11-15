# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os import listdir
from os.path import dirname, isdir, isfile, join, normpath, split as path_split

from .. import CondaError
from ..base.constants import ENVS_DIR_MAGIC_FILE, PREFIX_MAGIC_FILE, ROOT_ENV_NAME
from ..base.context import context
from ..common.compat import with_metaclass
from ..common.path import paths_equal, right_pad_os_sep
from ..gateways.disk.create import create_envs_directory
from ..gateways.disk.read import yield_lines
from ..gateways.disk.test import file_path_is_writable

log = getLogger(__name__)


class EnvsDirectoryType(type):
    """
    This metaclass does basic caching of EnvsDirectory instance objects.
    """

    def __call__(cls, envs_dir):
        if isinstance(envs_dir, EnvsDirectory):
            return envs_dir
        elif envs_dir in EnvsDirectory._cache_:
            return EnvsDirectory._cache_[envs_dir]
        else:
            envs_directory_instance = super(EnvsDirectoryType, cls).__call__(envs_dir)
            EnvsDirectory._cache_[envs_dir] = envs_directory_instance
            return envs_directory_instance


@with_metaclass(EnvsDirectoryType)
class EnvsDirectory(object):
    _cache_ = {}
    _is_writable = None

    def __init__(self, envs_dir):
        self.envs_dir = normpath(envs_dir)
        self.root_dir = dirname(envs_dir)
        self.catalog_file = join(envs_dir, ENVS_DIR_MAGIC_FILE)

    @property
    def is_writable(self):
        # lazy and cached
        # This method takes the action of creating an empty package cache if it does not exist.
        #   Logic elsewhere, both in conda and in code that depends on conda, seems to make that
        #   assumption.
        if self._is_writable is None:
            if isfile(join(self.envs_dir, ENVS_DIR_MAGIC_FILE)):
                self._is_writable = file_path_is_writable(self.catalog_file)
            else:
                log.debug("env directory '%s' does not exist", self.envs_dir)
                self._is_writable = create_envs_directory(self.envs_dir)
        return self._is_writable

    def raise_if_not_writable(self):
        if not self.is_writable:
            from ..exceptions import NotWritableError
            raise NotWritableError(self.catalog_file)
        return True

    @classmethod
    def env_name(cls, prefix):
        if not prefix:
            return None
        if paths_equal(prefix, context.root_prefix):
            return 'base'
        maybe_envs_dir, maybe_name = path_split(prefix)
        for envs_dir in context.envs_dirs:
            if paths_equal(envs_dir, maybe_envs_dir):
                return maybe_name
        return prefix

    @classmethod
    def first_writable(cls, envs_dirs=None):
        return cls.all_writable(envs_dirs)[0]

    @classmethod
    def all_writable(cls, envs_dirs=None):
        _all = cls.all(envs_dirs)
        writable_caches = tuple(ed for ed in _all if ed.is_writable)
        if not writable_caches:
            _all_envs_dirs = tuple(ed.envs_dir for ed in _all)
            raise CondaError("No writable envs directories found in\n"
                             "%s" % _all_envs_dirs)
        return writable_caches

    @classmethod
    def all(cls, envs_dirs=None):
        if envs_dirs is None:
            envs_dirs = context.envs_dirs
        else:
            envs_dirs = tuple(normpath(d) for d in envs_dirs)
        return tuple(cls(ed) for ed in envs_dirs)

    @classmethod
    def get_envs_directory_for_prefix(cls, prefix_path):
        prefix_path = right_pad_os_sep(normpath(prefix_path))

        for ed in context.envs_dirs:
            edo = cls(ed)
            if prefix_path.startswith(right_pad_os_sep(edo.root_dir)):
                return edo

        return cls.first_writable()

    @staticmethod
    def is_conda_environment(prefix):
        return isdir(prefix) and isfile(join(prefix, PREFIX_MAGIC_FILE))

    def to_prefix(self, env_name):
        if env_name in (None, ROOT_ENV_NAME, 'root'):
            return self.root_dir
        else:
            return join(self.envs_dir, env_name)

    def register_env(self, location):
        location = normpath(location)

        if "placehold_pl" in location:
            # Don't record envs created by conda-build.
            return

        envs_dir, env_name = path_split(location)

        if paths_equal(envs_dir, self.envs_dir):
            # Nothing to do.  We're not recording named envs in environments.txt
            return

        if paths_equal(location, self.root_dir):
            # Nothing to do.  We don't record the root location in environments.txt
            return

        if location in yield_lines(self.catalog_file):
            # Nothing to do. Location is already recorded in a known environments.txt file.
            return

        assert self.is_writable
        with open(self.catalog_file, 'a') as fh:
            fh.write(location)
            fh.write('\n')

    def unregister_env(self, location):
        if isdir(location):
            meta_dir = join(location, 'conda-meta')
            if isdir(meta_dir):
                meta_dir_contents = listdir(meta_dir)
                if len(meta_dir_contents) > 1:
                    # if there are any files left other than 'conda-meta/history'
                    #   then don't unregister
                    return

        self._clean_environments_txt(location)

    def _clean_environments_txt(self, remove_location=None):
        environments_txt_lines = list(yield_lines(self.catalog_file))

        try:
            location = normpath(remove_location or '')
            idx = environments_txt_lines.index(location)
            del environments_txt_lines[idx]
        except ValueError:
            # remove_location was not in list.  No problem, just move on.
            pass

        real_prefixes = tuple(p for p in environments_txt_lines if self.is_conda_environment(p))
        if self.is_writable:
            with open(self.catalog_file, 'w') as fh:
                fh.write('\n'.join(real_prefixes))
        return real_prefixes

    def list_envs(self):
        for path in listdir(self.envs_dir):
            if self.is_conda_environment(join(self.envs_dir, path)):
                yield path
        for path in self._clean_environments_txt():
            yield path
        if self.is_conda_environment(self.root_dir):
            yield self.root_dir

    @classmethod
    def list_all_envs(cls, envs_dirs=None):
        if envs_dirs is None:
            envs_dirs = context.envs_dirs
        all_envs = set()
        for envs_dir in envs_dirs:
            all_envs.update(cls(envs_dir).list_envs())
        return sorted(all_envs)
