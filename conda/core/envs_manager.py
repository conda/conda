# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import getLogger
from os import getcwd, listdir
from os.path import basename, dirname, isdir, isfile, join, normpath

from copy import deepcopy

from .. import CondaError
from .._vendor.auxlib.collection import first
from .._vendor.auxlib.entity import EntityEncoder
from .._vendor.auxlib.ish import dals
from .._vendor.auxlib.path import expand
from ..base.constants import ENVS_DIR_MAGIC_FILE, ROOT_ENV_NAME
from ..base.context import context
from ..common.compat import with_metaclass, text_type, range
from ..common.path import ensure_pad, right_pad_os_sep, win_path_ok
from ..exceptions import CondaEnvironmentNotFoundError, CondaValueError
from ..gateways.disk.create import create_envs_directory
from ..gateways.disk.test import file_path_is_writable
from ..models.dist import Dist

try:
    from cytoolz.itertoolz import concatv, groupby
except ImportError:
    from .._vendor.toolz.itertoolz import concatv, groupby

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
    """
    This class manages the `envs/catalog.json` file.

    The 'registered_envs' key is a list of known environment locations.  These locations need
    not be within the `envs` directory.  Each entry in the 'registered_envs/ list is a map
    containing two fields:

        name: the designated name of the environment, usually basename(location)
        location: the full path to the environment location

    The 'leased_paths' key is used for private environments, and specifically for executable paths
    to be mapped from the root environment one level above the `envs` directory into a private
    environment contained within the envs directory.  The 'leased_paths' key is a list, with each
    leased path entry being a map containing the following keys:

        _path: short path for the leased path, using forward slashes
        target_path: the full path to the executable in the private env
        target_prefix: the full path to the private environment
        leased_path: the full path for the lease in the root prefix
        package_name: the package holding the lease

    The 'preferred_env_packages' key is a list of packages associated with a private env, and
    therefore potentially having application entry points in the root env.  Each
    'preferred_env_packages' entry has the following keys:

        package_name: package name
        conda_meta_path: path to the package's conda-meta/*.json file within the target_prefix

    A preferred env package cannot also be installed in the root env.

    """
    _cache_ = {}
    _is_writable = None

    def __init__(self, envs_dir):
        self.envs_dir = normpath(envs_dir)
        self.root_dir = dirname(envs_dir)
        self.catalog_file = join(envs_dir, ENVS_DIR_MAGIC_FILE)

        self._init_dir()

    def _init_dir(self):
        self._envs_dir_data = self._read_raw_data()

    def _read_raw_data(self):
        # TODO: move this to conda.gateways.disk
        if isfile(self.catalog_file):
            with open(self.catalog_file) as fh:
                return json.loads(fh.read().strip())
        else:
            return {}

    def write_to_disk(self):
        # TODO: move this to conda.gateways.disk
        _data = {}
        if self._registered_envs:
            _data['registered_envs'] = self._registered_envs
        if self._leased_paths:
            _data['leased_paths'] = self._leased_paths
        if self._preferred_env_packages:
            _data['preferred_env_packages'] = self._preferred_env_packages

        if _data:
            if not self.is_writable:
                raise RuntimeError()
            with open(self.catalog_file, 'w') as fh:
                fh.write(json.dumps(_data, indent=2, sort_keys=True,
                                    separators=(',', ': '), cls=EntityEncoder))

    def _set_state(self, envs_dir_state):
        self._envs_dir_data = envs_dir_state  # TODO: find a better way

    def _get_state(self):
        return deepcopy(self._envs_dir_data)  # TODO: find a better way

    @property
    def _registered_envs(self):
        # mutable structure for use within this class
        return self._envs_dir_data.setdefault('registered_envs', [])

    @property
    def _leased_paths(self):
        # mutable structure for use within this class
        return self._envs_dir_data.setdefault('leased_paths', [])

    @property
    def _preferred_env_packages(self):
        # mutable structure for use within this class
        return self._envs_dir_data.setdefault('preferred_env_packages', [])

    @property
    def is_writable(self):
        # lazy and cached
        # This method takes the action of creating an empty package cache if it does not exist.
        #   Logic elsewhere, both in conda and in code that depends on conda, seems to make that
        #   assumption.
        if self._is_writable is None:
            if isdir(self.envs_dir):
                self._is_writable = file_path_is_writable(self.catalog_file)
            else:
                log.debug("env directory '%s' does not exist", self.envs_dir)
                self._is_writable = create_envs_directory(self.envs_dir)
        return self._is_writable

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
    def locate_prefix_by_name(cls, name, envs_dirs=None):
        """Find the location of a prefix given a conda env name."""
        if name == ROOT_ENV_NAME:
            return context.root_prefix

        for envs_dir in concatv(envs_dirs or context.envs_dirs, (getcwd(),)):
            prefix = join(envs_dir, name)
            if isdir(prefix):
                return prefix

        raise CondaEnvironmentNotFoundError(name)

    @classmethod
    def get_envs_directory_for_prefix(cls, prefix_path):
        prefix_path = right_pad_os_sep(normpath(prefix_path))

        for ed in context.envs_dirs:
            edo = cls(ed)
            if prefix_path.startswith(right_pad_os_sep(edo.root_dir)):
                return edo

        return cls.first_writable()

    @staticmethod
    def preferred_env_to_prefix(preferred_env):
        if preferred_env is None:
            return context.root_prefix
        else:
            return join(context.root_prefix, 'envs', ensure_pad(preferred_env, '_'))

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write_to_disk()

    # ############################
    # registered envs
    # ############################

    def to_prefix(self, env_name):
        if env_name in (None, ROOT_ENV_NAME):
            return self.root_dir
        else:
            return join(self.envs_dir, ensure_pad(env_name))

    def get_registered_env_by_name(self, env_name, default=None):
        if env_name is None:
            return default
        env_entry = next((renv for renv in self._registered_envs if renv.get('name') == env_name), default)
        return env_entry

    def get_registered_env_by_location(self, location, default=None):
        location = normpath(location)
        env_entry = next((renv for renv in self._registered_envs if renv['location'] == location), default)
        return env_entry

    def register_env(self, location):
        location = normpath(location)

        # figure out what the env name of the location is
        if location == self.root_dir:
            env_name = ROOT_ENV_NAME
        elif dirname(location) == self.envs_dir:
            env_name = basename(location)
        else:
            env_name = None

        # env name might already exist
        current_entry = self.get_registered_env_by_name(env_name)
        if env_name and current_entry:
            assert current_entry['location'] == location
            return

        # env location might already exist
        current_entry = self.get_registered_env_by_location(location)
        if current_entry:
            assert current_entry.get('name') is None
            return

        # finally, add a new entry
        self._registered_envs.append({
            'name': env_name,
            'location': location,
        })

    def unregister_env(self, location):
        if isdir(location):
            meta_dir = join(location, 'conda-meta')
            if isdir(meta_dir):
                meta_dir_contents = listdir(meta_dir)
                if len(meta_dir_contents) > 1:
                    # if there are any files left other than 'conda-meta/history'
                    #   then don't unregister
                    return

        idx = next((q for q, env_record in enumerate(self._registered_envs) if env_record['location'] == location), None)
        if idx is not None:
            self._registered_envs.pop(idx)


    # ############################
    # leased paths
    # ############################

    def get_leased_path_entry(self, target_short_path, default=None):
        current_lp = next((lp for lp in self._leased_paths if lp['_path'] == target_short_path), default)
        return current_lp

    def assert_path_not_leased(self, target_short_path):
        current_lp = self.get_leased_path_entry(target_short_path)
        if current_lp:
            message = dals("""
            A path in '%(root_prefix)s'
            is already in use by another environment.
              path: %(target_short_path)s
              current prefix: %(current_prefix)s
            """)
            current_prefix = current_lp['target_prefix']
            raise CondaError(message,
                             root_prefix=self.root_dir,
                             target_short_path=target_short_path,
                             current_prefix=current_prefix)

    def add_leased_path(self, target_prefix, target_short_path, root_prefix, package_name):
        self.assert_path_not_leased(target_short_path)

        leased_path_entry = {
            "_path": target_short_path,
            "target_path": join(target_prefix, win_path_ok(target_short_path)),
            "target_prefix": target_prefix,
            "leased_path": join(root_prefix, win_path_ok(target_short_path)),
            "package_name": package_name,
        }

        self._leased_paths.append(leased_path_entry)

    def remove_leased_path(self, target_short_path):
        lp_idx = next((q for q, lp in enumerate(self._leased_paths) if lp['_path'] == target_short_path), None)
        if lp_idx is not None:
            self._leased_paths.pop(lp_idx)

    def get_leased_path_entries_for_package(self, package_name):
        return tuple(lpe for lpe in self._leased_paths if lpe['package_name'] == package_name)



    # ############################
    # preferred env packages
    # ############################

    def add_preferred_env_package(self, preferred_env_name, package_name, conda_meta_path, requested_spec):
        # assert package of same name not already installed in root env
        # assert there's not already a similar entry
        preferred_env_packages_entry = {
            'package_name': package_name,
            'conda_meta_path': conda_meta_path,
            'preferred_env_name': ensure_pad(preferred_env_name),
            'requested_spec': text_type(requested_spec),
        }
        self._preferred_env_packages.append(preferred_env_packages_entry)

    def remove_preferred_env_package(self, package_name):
        lp_idx = next((q for q, lp in enumerate(self._preferred_env_packages) if lp['package_name'] == package_name), None)
        package_record = self._preferred_env_packages.pop(lp_idx) if lp_idx is not None else None

        if package_record:
            q = 0
            while q < len(self._leased_paths):
                lpr = self._leased_paths[q]
                if lpr['package_name'] == package_name:
                    self._leased_paths.pop(q)
                else:
                    q += 1

    def get_registered_preferred_env(self, package_name):
        pep = first(self._preferred_env_packages, lambda p: p['package_name'] == package_name)
        return pep and pep['preferred_env_name']

    def get_registered_packages(self):
        # returns Map[package_name, env_name]
        return {pep['package_name']: pep for pep in self._preferred_env_packages}

    def get_registered_packages_keyed_on_env_name(self):
        get_env_name = lambda x: x['preferred_env_name']
        return groupby(get_env_name, self._preferred_env_packages)

    def prefix_if_in_private_env(self, spec_str):
        # TODO: get rid of this
        package_name = spec_str.split()[0]
        pep = first(self._preferred_env_packages, lambda p: p['package_name'] == package_name)
        return join(self.envs_dir, pep['preferred_env_name']) if pep else None

    def get_preferred_env_package(self, spec_str):
        # TODO: get rid of this
        package_name = spec_str.split()[0]
        pep = first(self._preferred_env_packages, lambda p: p['package_name'] == package_name)
        if pep:
            json_file_name = basename(pep['conda_meta_path'])
            return Dist(json_file_name[:-5])
        else:
            return None


def get_prefix(ctx, args, search=True):
    """Get the prefix to operate in

    Args:
        ctx: the context of conda
        args: the argparse args from the command line
        search: whether search for prefix

    Returns: the prefix
    Raises: CondaEnvironmentNotFoundError if the prefix is invalid
    """
    if getattr(args, 'name', None):
        if '/' in args.name:
            raise CondaValueError("'/' not allowed in environment name: %s" %
                                  args.name, getattr(args, 'json', False))
        if args.name == ROOT_ENV_NAME:
            return ctx.root_dir
        if search:
            return EnvsDirectory.locate_prefix_by_name(args.name)
        else:
            # need first writable envs_dir
            envs_dir = EnvsDirectory.first_writable().envs_dir
            return join(envs_dir, args.name)
    elif getattr(args, 'prefix', None):
        return expand(args.prefix)
    else:
        return ctx.default_prefix
