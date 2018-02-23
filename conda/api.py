# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from .common.constants import NULL
from .core.package_cache_data import PackageCacheData as _PackageCacheData
from .core.prefix_data import PrefixData as _PrefixData
from .core.solve import Solver as _Solver, DepsModifier as _DepsModifier
from .core.subdir_data import SubdirData as _SubdirData
from .models.channel import Channel


DepsModifier = _DepsModifier
"""Flags to enable alternate handling of dependencies."""


class Solver(object):
    """
    A high-level API to conda's solving logic. Three public methods are provided to access a
    solution in various forms.

      * :meth:`solve_final_state`
      * :meth:`solve_for_diff`
      * :meth:`solve_for_transaction`

    """

    def __init__(self, prefix, channels, subdirs=(), specs_to_add=(), specs_to_remove=()):
        """
        Args:
            prefix (str):
                The conda prefix / environment location for which the :class:`Solver`
                is being instantiated.
            channels (Sequence[:class:`Channel`]):
                A prioritized list of channels to use for the solution.
            subdirs (Sequence[str]):
                A prioritized list of subdirs to use for the solution.
            specs_to_add (Set[:class:`MatchSpec`]):
                The set of package specs to add to the prefix.
            specs_to_remove (Set[:class:`MatchSpec`]):
                The set of package specs to remove from the prefix.

        """
        self._internal = _Solver(prefix, channels, subdirs, specs_to_add, specs_to_remove)

    def solve_final_state(self, deps_modifier=NULL, prune=NULL, ignore_pinned=NULL,
                          force_remove=NULL):
        """Gives the final, solved state of the environment.

        Args:
            deps_modifier (DepsModifier):
                An optional flag indicating special solver handling for dependencies. The
                default solver behavior is to be as conservative as possible with dependency
                updates (in the case the dependency already exists in the environment), while
                still ensuring all dependencies are satisfied.  Options include
                    * NO_DEPS
                    * ONLY_DEPS
                    * UPDATE_DEPS
                    * UPDATE_DEPS_ONLY_DEPS
            prune (bool):
                If ``True``, the solution will not contain packages that were
                previously brought into the environment as dependencies but are no longer
                required as dependencies and are not user-requested.
            ignore_pinned (bool):
                If ``True``, the solution will ignore pinned package configuration
                for the prefix.
            force_remove (bool):
                Forces removal of a package without removing packages that depend on it.

        Returns:
            Tuple[PackageRef]:
                In sorted dependency order from roots to leaves, the package references for
                the solved state of the environment.

        """
        return self._internal.solve_final_state(deps_modifier, prune, ignore_pinned,
                                                force_remove)

    def solve_for_diff(self, deps_modifier=NULL, prune=NULL, ignore_pinned=NULL,
                       force_remove=NULL, force_reinstall=False):
        """Gives the package references to remove from an environment, followed by
        the package references to add to an environment.

        Args:
            deps_modifier (DepsModifier):
                See :meth:`solve_final_state`.
            prune (bool):
                See :meth:`solve_final_state`.
            ignore_pinned (bool):
                See :meth:`solve_final_state`.
            force_remove (bool):
                See :meth:`solve_final_state`.
            force_reinstall (bool):
                For requested specs_to_add that are already satisfied in the environment,
                    instructs the solver to remove the package and spec from the environment,
                    and then add it back--possibly with the exact package instance modified,
                    depending on the spec exactness.

        Returns:
            Tuple[PackageRef], Tuple[PackageRef]:
                A two-tuple of PackageRef sequences.  The first is the group of packages to
                remove from the environment, in sorted dependency order from leaves to roots.
                The second is the group of packages to add to the environment, in sorted
                dependency order from roots to leaves.

        """
        return self._internal.solve_for_diff(deps_modifier, prune, ignore_pinned,
                                             force_remove, force_reinstall)

    def solve_for_transaction(self, deps_modifier=NULL, prune=NULL, ignore_pinned=NULL,
                              force_remove=NULL, force_reinstall=False):
        """Gives an UnlinkLinkTransaction instance that can be used to execute the solution
        on an environment.

        Args:
            deps_modifier (DepsModifier):
                See :meth:`solve_final_state`.
            prune (bool):
                See :meth:`solve_final_state`.
            ignore_pinned (bool):
                See :meth:`solve_final_state`.
            force_remove (bool):
                See :meth:`solve_final_state`.
            force_reinstall (bool):
                See :meth:`solve_for_diff`.

        Returns:
            UnlinkLinkTransaction:

        """
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
