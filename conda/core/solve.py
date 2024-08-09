# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""The classic solver implementation."""

from __future__ import annotations

from logging import getLogger
from os.path import exists, join
from typing import TYPE_CHECKING

from boltons.setutils import IndexedSet

from ..base.constants import REPODATA_FN
from ..base.context import context
from ..common.constants import NULL
from ..common.io import dashlist
from ..common.iterators import groupby_to_dict as groupby
from ..common.path import get_major_minor_version
from ..models.channel import Channel
from ..models.enums import NoarchType
from ..models.match_spec import MatchSpec
from ..models.prefix_graph import PrefixGraph
from .link import PrefixSetup, UnlinkLinkTransaction
from .prefix_data import PrefixData

if TYPE_CHECKING:
    from typing import Iterable

    from ..models.records import PackageRecord

log = getLogger(__name__)


class Solver:
    """
    A high-level API to conda's solving logic. Three public methods are provided to access a
    solution in various forms.

      * :meth:`solve_final_state`
      * :meth:`solve_for_diff`
      * :meth:`solve_for_transaction`: must be provided by a subclass.

    Subclasses must also provide an implementation for :meth:`_notify_conda_outdated`.
    """

    def __init__(
        self,
        prefix: str,
        channels: Iterable[Channel],
        subdirs: Iterable[str] = (),
        specs_to_add: Iterable[MatchSpec] = (),
        specs_to_remove: Iterable[MatchSpec] = (),
        repodata_fn: str = REPODATA_FN,
        command=NULL,
    ):
        """
        Args:
            prefix (str):
                The conda prefix / environment location for which the :class:`Solver`
                is being instantiated.
            channels (Sequence[:class:`Channel`]):
                A prioritized list of channels to use for the solution.
            subdirs (Sequence[str]):
                A prioritized list of subdirs to use for the solution.
            specs_to_add (set[:class:`MatchSpec`]):
                The set of package specs to add to the prefix.
            specs_to_remove (set[:class:`MatchSpec`]):
                The set of package specs to remove from the prefix.

        """
        self.prefix = prefix
        self._channels = channels or context.channels
        self.channels = IndexedSet(Channel(c) for c in self._channels)
        self.subdirs = tuple(s for s in subdirs or context.subdirs)
        self.specs_to_add = frozenset(MatchSpec.merge(s for s in specs_to_add))
        self.specs_to_add_names = frozenset(_.name for _ in self.specs_to_add)
        self.specs_to_remove = frozenset(MatchSpec.merge(s for s in specs_to_remove))
        self.neutered_specs = ()
        self._command = command

        assert all(s in context.known_subdirs for s in self.subdirs)
        self._repodata_fn = repodata_fn
        self._index = None
        self._r = None
        self._prepared = False
        self._pool_cache = {}

    def solve_for_transaction(
        self,
        update_modifier=NULL,
        deps_modifier=NULL,
        prune=NULL,
        ignore_pinned=NULL,
        force_remove=NULL,
        force_reinstall=NULL,
        should_retry_solve=False,
    ):
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
            should_retry_solve (bool):
                See :meth:`solve_final_state`.

        Returns:
            UnlinkLinkTransaction:

        """
        if self.prefix == context.root_prefix and context.enable_private_envs:
            # This path has the ability to generate a multi-prefix transaction. The basic logic
            # is in the commented out get_install_transaction() function below. Exercised at
            # the integration level in the PrivateEnvIntegrationTests in test_create.py.
            raise NotImplementedError()

        # run pre-solve processes here before solving for a solution
        context.plugin_manager.invoke_pre_solves(
            self.specs_to_add,
            self.specs_to_remove,
        )

        unlink_precs, link_precs = self.solve_for_diff(
            update_modifier,
            deps_modifier,
            prune,
            ignore_pinned,
            force_remove,
            force_reinstall,
            should_retry_solve,
        )
        # TODO: Only explicitly requested remove and update specs are being included in
        #   History right now. Do we need to include other categories from the solve?

        # run post-solve processes here before performing the transaction
        context.plugin_manager.invoke_post_solves(
            self._repodata_fn,
            unlink_precs,
            link_precs,
        )

        self._notify_conda_outdated(link_precs)
        return UnlinkLinkTransaction(
            PrefixSetup(
                self.prefix,
                unlink_precs,
                link_precs,
                self.specs_to_remove,
                self.specs_to_add,
                self.neutered_specs,
            )
        )

    def solve_for_diff(
        self,
        update_modifier=NULL,
        deps_modifier=NULL,
        prune=NULL,
        ignore_pinned=NULL,
        force_remove=NULL,
        force_reinstall=NULL,
        should_retry_solve=False,
    ) -> tuple[tuple[PackageRecord, ...], tuple[PackageRecord, ...]]:
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
            should_retry_solve (bool):
                See :meth:`solve_final_state`.

        Returns:
            tuple[PackageRef], tuple[PackageRef]:
                A two-tuple of PackageRef sequences.  The first is the group of packages to
                remove from the environment, in sorted dependency order from leaves to roots.
                The second is the group of packages to add to the environment, in sorted
                dependency order from roots to leaves.

        """
        final_precs = self.solve_final_state(
            update_modifier,
            deps_modifier,
            prune,
            ignore_pinned,
            force_remove,
            should_retry_solve,
        )
        unlink_precs, link_precs = diff_for_unlink_link_precs(
            self.prefix, final_precs, self.specs_to_add, force_reinstall
        )

        # assert that all unlink_precs are manageable
        unmanageable = groupby(lambda prec: prec.is_unmanageable, unlink_precs).get(
            True
        )
        if unmanageable:
            raise RuntimeError(
                f"Cannot unlink unmanageable packages:{dashlist(prec.record_id() for prec in unmanageable)}"
            )

        return unlink_precs, link_precs

    def solve_final_state(
        self,
        update_modifier=NULL,
        deps_modifier=NULL,
        prune=NULL,
        ignore_pinned=NULL,
        force_remove=NULL,
        should_retry_solve=False,
    ):
        """Gives the final, solved state of the environment.

        Args:
            update_modifier (UpdateModifier):
                An optional flag directing how updates are handled regarding packages already
                existing in the environment.

            deps_modifier (DepsModifier):
                An optional flag indicating special solver handling for dependencies. The
                default solver behavior is to be as conservative as possible with dependency
                updates (in the case the dependency already exists in the environment), while
                still ensuring all dependencies are satisfied.  Options include
                * NO_DEPS
                * ONLY_DEPS
                * UPDATE_DEPS
                * UPDATE_DEPS_ONLY_DEPS
                * FREEZE_INSTALLED
            prune (bool):
                If ``True``, the solution will not contain packages that were
                previously brought into the environment as dependencies but are no longer
                required as dependencies and are not user-requested.
            ignore_pinned (bool):
                If ``True``, the solution will ignore pinned package configuration
                for the prefix.
            force_remove (bool):
                Forces removal of a package without removing packages that depend on it.
            should_retry_solve (bool):
                Indicates whether this solve will be retried. This allows us to control
                whether to call find_conflicts (slow) in ssc.r.solve

        Returns:
            tuple[PackageRef]:
                In sorted dependency order from roots to leaves, the package references for
                the solved state of the environment.

        """
        raise NotImplementedError

    def _notify_conda_outdated(self, link_precs):
        raise NotImplementedError


def get_pinned_specs(prefix):
    """Find pinned specs from file and return a tuple of MatchSpec."""
    pinfile = join(prefix, "conda-meta", "pinned")
    if exists(pinfile):
        with open(pinfile) as f:
            from_file = (
                i
                for i in f.read().strip().splitlines()
                if i and not i.strip().startswith("#")
            )
    else:
        from_file = ()

    return tuple(
        MatchSpec(spec, optional=True)
        for spec in (*context.pinned_packages, *from_file)
    )


def diff_for_unlink_link_precs(
    prefix,
    final_precs,
    specs_to_add=(),
    force_reinstall=NULL,
) -> tuple[tuple[PackageRecord, ...], tuple[PackageRecord, ...]]:
    # Ensure final_precs supports the IndexedSet interface
    if not isinstance(final_precs, IndexedSet):
        assert hasattr(
            final_precs, "__getitem__"
        ), "final_precs must support list indexing"
        assert hasattr(
            final_precs, "__sub__"
        ), "final_precs must support set difference"

    previous_records = IndexedSet(PrefixGraph(PrefixData(prefix).iter_records()).graph)
    force_reinstall = (
        context.force_reinstall if force_reinstall is NULL else force_reinstall
    )

    unlink_precs = previous_records - final_precs
    link_precs = final_precs - previous_records

    def _add_to_unlink_and_link(rec):
        link_precs.add(rec)
        if prec in previous_records:
            unlink_precs.add(rec)

    # If force_reinstall is enabled, make sure any package in specs_to_add is unlinked then
    # re-linked
    if force_reinstall:
        for spec in specs_to_add:
            prec = next((rec for rec in final_precs if spec.match(rec)), None)
            assert prec
            _add_to_unlink_and_link(prec)

    # add back 'noarch: python' packages to unlink and link if python version changes
    python_spec = MatchSpec("python")
    prev_python = next(
        (rec for rec in previous_records if python_spec.match(rec)), None
    )
    curr_python = next((rec for rec in final_precs if python_spec.match(rec)), None)
    gmm = get_major_minor_version
    if (
        prev_python
        and curr_python
        and gmm(prev_python.version) != gmm(curr_python.version)
    ):
        noarch_python_precs = (p for p in final_precs if p.noarch == NoarchType.python)
        for prec in noarch_python_precs:
            _add_to_unlink_and_link(prec)

    unlink_precs = IndexedSet(
        reversed(sorted(unlink_precs, key=lambda x: previous_records.index(x)))
    )
    link_precs = IndexedSet(sorted(link_precs, key=lambda x: final_precs.index(x)))
    return tuple(unlink_precs), tuple(link_precs)
