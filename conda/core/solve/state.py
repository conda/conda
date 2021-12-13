"""
Solver-agnostic logic to expose the prefix state to the solver.
"""

from collections import defaultdict, Mapping, MutableMapping
from types import MappingProxyType
from typing import Any, Hashable, Iterable, Union, Optional, Tuple
from os import PathLike
import logging
import functools

from conda.exceptions import RawStrUnsatisfiableError

from ... import CondaError
from ...auxlib.ish import dals
from ...base.constants import DepsModifier, UpdateModifier
from ...base.context import context
from ...common.io import dashlist
from ...common.path import get_major_minor_version, paths_equal
from ...history import History
from ...models.match_spec import MatchSpec
from ...models.records import PackageRecord
from ..index import _supplement_index_with_system
from ..prefix_data import PrefixData
from .classic import get_pinned_specs


class TrackedMap(MutableMapping):
    """
    Implements a dictionary-like interface with self-logging capabilities.

    Each item in the dictionary can be annotated with a ``reason`` of type ``str``.
    Since a keyword argument is needed, this is only doable via the ``.set()`` method
    (or any of the derivative methods that call it, like ``.update()``). With normal
    ``dict`` assignment (à la ``d[key] = value``), ``reason`` will be None.

    Reasons are kept in a dictionary of lists, so a history of reasons is kept for each
    key present in the dictionary. Reasons for a given ``key`` can be checked with
    ``.reasons_for(key)``.

    Regardless the value of ``reason``, assignments, updates and deletions will be logged
    for easy debugging. It is in principle possible to track where each key came from
    by reading the logs, since the stack level is matched to the originating operation.

    ``.set()`` and ``.update()`` also support an ``overwrite`` boolean option, set to
    True by default. If False, an existing key will _not_ be overwritten with the
    new value.

    Parameters
    ----------
    name
        A short identifier for this tracked map. Useful for logging.
    data
        Initial data for this object. It can be a dictionary, an iterable of key-value
        pairs, or another ``TrackedMap`` instance. If given a ``TrackedMap`` instance,
        its data and reasons will be copied over, instead of wrapped, to avoid recursion.
    reason
        Optionally, a reason on why this object was initialized with such data. Ignored
        if no data is provided.

    Examples
    --------
    >>> TrackedMap("example", data={"key": "value"}, reason="Initialization)
    >>> tm = TrackedMap("example")
    >>> tm.set("key", "value", reason="First value")
    >>> tm.update({"another_key": "another_value"}, reason="Second value")
    >>> tm["third_key"] = "third value"
    >>> tm[key]
        "value"
    >>> tm.reasons_for(key)
        ["First value"]
    >>> tm["third_key"]
        "third value"
    >>> tm.reasons_for("third_key")
        [None]
    """
    def __init__(self, name: str, data: Optional[Union["TrackedMap", Iterable[Iterable], dict]] = None, reason: Optional[str] = None):
        self._name = name
        logging_name = f"{__name__}::{self.__class__.__name__}"
        if name:
            logging_name += f"::{name}"
        self._logger = logging.getLogger(logging_name)

        if isinstance(data, TrackedMap):
            self._data = data._data.copy()
            self._reasons = data._reasons.copy()
        else:
            self._data = {}
            self._reasons = defaultdict(list)
            self.update(data, reason=reason)

    def _set(self, key, value, *, reason: Optional[str] = None, overwrite=True, _level=3):
        try:
            old = self._data[key]
            old_reason = self._reasons.get(key, [None])[-1]
            msg = f"{self._name}[{key}] (={old}, reason={old_reason}) updated to '{value}'"
            write = overwrite
        except KeyError:
            msg = f"{self._name}[{key}] set to '{value}'"
            write = True

        if write:
            if reason:
                msg += f' (reason={reason})'
                self._reasons[key].append(reason)
            self._data[key] = value
        else:
            msg = (
                f"{self._name}[{key}] (={old}, reason={old_reason}) wanted new value '{value}' "
                f"(reason={reason}) but stayed the same due to overwrite=False."
            )

        self._logger.debug(msg, stacklevel=_level)

    @property
    def name(self):
        return self._name

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key: Hashable):
        return self._data[key]

    def __setitem__(self, key: Hashable, value: Any):
        self._set(key, value)

    def __delitem__(self, key: Hashable):
        del self._data[key]
        self._reasons.pop(key, None)
        self._logger.debug(f'{self._name}[{key}] was deleted', stacklevel=2)

    def pop(self, key: Hashable, *, reason: Optional[str] = None) -> Any:
        """
        Remove a key-value pair and return the value. A reason can be provided
        for logging purposes, but it won't be stored in the object.
        """
        value = self._data.pop(key)
        self._reasons.pop(key, None)
        msg = f'{self._name}[{key}] (={value}) was deleted'
        if reason:
            msg += f" (reason={reason})"
        self._logger.debug(msg, stacklevel=2)
        return value

    def popitem(self, key: Hashable, *, reason: Optional[str] = None) -> Tuple[Hashable, Any]:
        """
        Remove and return a key-value pair. A reason can be provided for logging purposes,
        but it won't be stored in the object.
        """
        key, value = self._data.popitem(key)
        self._reasons.pop(key, None)
        msg = f'{self._name}[{key}] (={value}) was deleted'
        if reason:
            msg += f" (reason={reason})"
        self._logger.debug(msg, stacklevel=2)
        return key, value

    def clear(self, reason: Optional[str] = None):
        """
        Remove all entries in the map. A reason can be provided for logging purposes,
        but it won't be stored in the object.
        """
        self._data.clear()
        self._reasons.clear()
        msg = f'{self._name} was cleared'
        if reason:
            msg += f" (reason={reason})"
        self._logger.debug(msg)

    def update(self, data: Union[dict, Iterable], *, reason: Optional[str] = None, overwrite: bool = True):
        """
        Update the dictionary with a reason. Note that keyword arguments
        are not supported in this specific implementation, so you can only
        update a dictionary with another dictionary or iterable as a
        positional argument. This is done so `reason` and `overwrite` can
        be used to control options instead of silently ignoring a potential
        entry in a ``**kwargs`` argument.
        """
        if hasattr(data, "keys"):
            for k in data.keys():
                self._set(k, data[k], reason=reason, overwrite=overwrite)
        else:
            for k, v in data:
                self._set(k, v, reason=reason, overwrite=overwrite)

    def set(self, key: Hashable, value: Any, *, reason: Optional[str] = None, overwrite: bool = True):
        """
        Set ``key`` to ``value``, optionally providing a ``reason`` why.

        Parameters
        ----------
        key
            Key to the passed value
        value
            Value
        reason
            A short description on why this key, value pair was added
        overwrite
            If False, do _not_ update the ``value`` for ``key`` if ``key``
            was already present in the dictionary.
        """
        self._set(key, value, reason=reason, overwrite=overwrite)

    def reasons_for(self, key: Hashable) -> Union[Iterable[Union[str, None]], None]:
        """
        Return the stored reasons for a given ``key``
        """
        return self._reasons.get(key)


class SolverInputState:
    """
    Helper object to provide the input data needed to compute the state that will be
    exposed to the solver.

    Parameters
    ----------
    prefix
        Path to the prefix we are operating on. This will be used to expose
        ``PrefixData``, ``History``, pinned specs, among others.
    requested
        The MatchSpec objects required by the user (either in the command line or
        through the Python API).
    update_modifier
        A value of ``UpdateModifier``, which has an effect on which specs are added
        to the final list. The default value here must match the default value in the
        ``context`` object.
    deps_modifier
        A value of ``DepsModifier``, which has an effect on which specs are added
        to the final list. The default value here must match the default value in the
        ``context`` object.
    ignore_pinned
        Whether pinned specs can be ignored or not. The default value here must match
        the default value in the ``context`` object.
    force_remove
        Remove the specs without solving the environment (which would also remove their)
        dependencies. The default value here must match the default value in the
        ``context`` object.
    force_reinstall
        Uninstall and install the computed records even if they were already satisfied
        in the given prefix. The default value here must match the default value in the
        ``context`` object.
    prune
        Remove dangling dependencies that ended up orphan. The default value here must
        match the default value in the ``context`` object.
    command
        The subcommand used to invoke this operation (e.g. ``create``, ``install``, ``remove``...).
        It can have an effect on the computed list of records.
    _pip_interop_enabled
        Internal only. Whether ``PrefixData`` will also expose packages not installed by
        ``conda`` (e.g. ``pip`` and others can put Python packages in the prefix).
    """
    def __init__(
        self,
        prefix: Union[str, bytes, PathLike],
        requested: Optional[Iterable[Union[str, MatchSpec]]] = (),
        update_modifier: Optional[UpdateModifier] = UpdateModifier.UPDATE_SPECS,
        deps_modifier: Optional[DepsModifier] = DepsModifier.NOT_SET,
        ignore_pinned: Optional[bool] = None,
        force_remove: Optional[bool] = False,
        force_reinstall: Optional[bool] = False,
        prune: Optional[bool] = False,
        command: Optional[str] = None,
        _pip_interop_enabled: Optional[bool] = None,
    ):
        self._prefix_data = PrefixData(prefix, pip_interop_enabled=_pip_interop_enabled)
        self._history = History(prefix).get_requested_specs_map()
        self._pinned = get_pinned_specs(prefix)
        self._aggressive_updates = {s.name for s in context.aggressive_update_packages}

        self._virtual = {}
        _supplement_index_with_system(self._virtual)

        self._requested = {}
        for spec in requested:
            spec = MatchSpec(spec)
            self._requested[spec.name] = spec

        self._update_modifier = update_modifier
        self._deps_modifier = deps_modifier
        self._ignore_pinned = ignore_pinned
        self._force_remove = force_remove
        self._force_reinstall = force_reinstall
        self._prune = prune
        self._command = command

        # special cases
        _do_not_remove = ('anaconda', 'conda', 'conda-build', 'python.app', 'console_shortcut', 'powershell_shortcut')
        self._do_not_remove = {p: MatchSpec(p) for p in _do_not_remove}

    @property
    def prefix_data(self) -> PrefixData:
        """
        A direct reference to the ``PrefixData`` object for the given ``prefix``.
        You will usually use this object through the ``installed`` property.
        """
        return self._prefix_data

    # Prefix state pools

    @property
    def installed(self) -> Mapping[str, PackageRecord]:
        """
        This exposes the installed packages in the prefix. Note that a ``PackageRecord``
        can generate an equivalent ``MatchSpec`` object with ``.to_match_spec()``.
        """
        return MappingProxyType(self.prefix_data._prefix_records)

    @property
    def history(self) -> Mapping[str, MatchSpec]:
        """
        These are the specs that the user explicitly asked for in previous operations
        on the prefix. See :class:`History` for more details.
        """
        return MappingProxyType(self._history)

    @property
    def pinned(self) -> Mapping[str, MatchSpec]:
        """
        These specs represent hard constrains on what package versions can be installed
        on the environment. The packages here returned don't need to be already installed.

        If ``ignore_pinned`` is True, this returns an empty dictionary.
        """
        if self.ignore_pinned:
            return MappingProxyType({})
        return MappingProxyType(self._pinned)

    @property
    def virtual(self) -> Mapping[str, MatchSpec]:
        """
        System properties exposed as virtual packages (e.g. ``__glibc=2.17``). These packages
        cannot be (un)installed, they only represent constrains for other packages. By convention,
        their names start with a double underscore.
        """
        return MappingProxyType(self._virtual)

    @property
    def aggressive_updates(self) -> Mapping[str, MatchSpec]:
        """
        Packages that the solver will always try to update. As such, they will never have an associated
        version or build constrain. Note that the packages here returned do not need to be installed.
        """
        return MappingProxyType(self._aggressive_updates)

    @property
    def do_not_remove(self) -> Mapping[str, MatchSpec]:
        """
        Packages that are protected by the solver so they are not accidentally removed. This list is
        not configurable, but hardcoded for legacy reasons.
        """
        return MappingProxyType(self._do_not_remove)

    # User requested pools

    @property
    def requested(self) -> Mapping[str, MatchSpec]:
        """
        Packages that the user has explicitly asked for in this operation.
        """
        return MappingProxyType(self._requested)

    # NOTE: All the blocks below can (and should) be expressed through dataclasses
    # For example .installing should become .command.install, and .with_update_all
    # could be .update_modifier.update_all

    # Types of commands

    @property
    def is_installing(self) -> bool:
        """
        True if the used subcommand was ``install``.
        """
        return self._command == "install"

    @property
    def is_updating(self) -> bool:
        """
        True if the used subcommand was ``update``.
        """
        return self._command == "update"

    @property
    def is_creating(self) -> bool:
        """
        True if the used subcommand was ``create``.
        """
        return self._command == "create"

    @property
    def is_removing(self) -> bool:
        """
        True if the used subcommand was ``remove``.
        """
        return self._command == "remove"

    # Update modifiers

    @property
    def update_modifier(self) -> UpdateModifier:
        return self._update_modifier

    @property
    def with_update_specs(self) -> UpdateModifier:
        return str(self._update_modifier) == str(UpdateModifier.UPDATE_SPECS)

    @property
    def with_update_all(self) -> UpdateModifier:
        return str(self._update_modifier) == str(UpdateModifier.UPDATE_ALL)

    @property
    def with_update_deps(self) -> UpdateModifier:
        return str(self._update_modifier) == str(UpdateModifier.UPDATE_DEPS)

    @property
    def with_freeze_installed(self) -> UpdateModifier:
        return str(self._update_modifier) == str(UpdateModifier.FREEZE_INSTALLED)

    @property
    def with_specs_satisfied_skip_solve(self) -> UpdateModifier:
        return str(self._update_modifier) == str(UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE)

    # Deps modifiers

    @property
    def deps_modifier(self) -> DepsModifier:
        return self._deps_modifier

    @property
    def with_deps(self) -> DepsModifier:
        return str(self._deps_modifier) == str(DepsModifier.NOT_SET)

    @property
    def with_no_deps(self) -> DepsModifier:
        return str(self._deps_modifier) == str(DepsModifier.NO_DEPS)

    @property
    def with_only_deps(self) -> DepsModifier:
        return str(self._deps_modifier) == str(DepsModifier.ONLY_DEPS)

    # Other flags

    @property
    def ignore_pinned(self) -> bool:
        return self._ignore_pinned

    @property
    def force_remove(self) -> bool:
        return self._force_remove

    @property
    def force_reinstall(self) -> bool:
        return self._force_reinstall

    @property
    def prune(self) -> bool:
        return self._prune


class SolverOutputState(Mapping):
    """
    This is the main mutable object we will massage before passing the
    result of the computation to the solver. It will also store the result
    of the solve.

    Its main intent is to populate the different spec pools with MatchSpec
    objects obtained from an ``SolverInputState`` instance.

    The main result of this operation is available through ``.pool_items()``,
    which returns ``str, MatchSpec`` tuples, mimicking ``dict.items()``. The
    key here is the pool name, which stands for a reason why this spec
    made it to the final list.

    The pool merging logic is done in ``._populate_pools()``.

    All of these pools will map package names (``str``) to ``MatchSpec`` (_specs_ in short)
    objects. A quick note on these objects:

    * They are a query language for packages, based on the ``PackageRecord`` schema.
      ``PackageRecord`` objects is how packages that are already installed are represented. This
      is what you get from ``PrefixData.iter_records()``. Since they are related,
      ``MatchSpec`` objects can be created from a ``PackageRecord``.
    * ``MatchSpec`` objects also feature fields like ``target`` and ``optional``. These are,
      essentially, used by the low-level classic solver (:class:`conda.resolve.Resolve`) to mark
      specs as items they can optionally play with to satisfy the solver constrains. A ``target``
      marked spec is _soft-pinned_ in the sense that the solver will try to satisfy that but it
      will stop trying if it gets in the way, so you might end up a different version or build.
      ``optional`` seems to be in the same lines, but maybe the entire spec can be dropped from the
      request? The key idea here is that these two fields might not be directly usable by the solver,
      but it might need some custom adaptation. For example, for ``libmamba`` we might need a separate
      pool that can be configured as a flexible task. See more details in the first comment of
      ``conda.core.solve.classic.Solver._add_specs``
    """
    def __init__(
        self,
        *,
        specs: Optional[Mapping[str, MatchSpec]] = None,
        records: Optional[Mapping[str, PackageRecord]] = None,
        neutered: Optional[Mapping[str, MatchSpec]] = None,
        conflicts: Optional[Mapping[str, MatchSpec]] = None,
        solver_input_state: Optional[SolverInputState] = None,

        # NOTE: Ignore this gigantic list of pools

        # conflicting_installed: Optional[Mapping] = None,
        # deps_modifier: Optional[Mapping] = None,
        # history: Optional[Mapping] = None,
        # installed: Optional[Mapping] = None,
        # neutered: Optional[Mapping] = None,
        # requested: Optional[Mapping] = None,
        # update_modifier: Optional[Mapping] = None,
        # virtual_system: Optional[Mapping] = None,
    ):
        # spec pools
        # # NOTE: Redo this. They shouldn't be reasons, but instructions to the solver
        # # about how strict / flexible the specs requested are. Reasons are in each
        # # TrackedMap instance if needed.
        # # self._requested = TrackedMap("requested", data=(requested or {}))
        # # self._installed = TrackedMap("installed", data=(installed or {}))
        # # self._conflicting_installed = TrackedMap("conflicting_installed", data=(conflicting_installed or {}))
        # # self._history = TrackedMap("history", data=(history or {}))
        # # self._neutered = TrackedMap("neutered", data=(neutered or {}))
        # # self._update_modifier = TrackedMap("update_modifier", data=(update_modifier or {}))
        # # self._deps_modifier = TrackedMap("deps_modifier", data=(deps_modifier or {}))
        # # self._virtual_system = TrackedMap("virtual_system", data=(virtual_system or {}))
        # # The spec pools are:

        # # * ``installed``: packages that were already installed and shouldn't be modified.
        # #     These packages are pinned to a specific strict version (``numpy=1.7.8=0``).
        # #     In principle, only one package should be available for this expression.
        # # * ``conflicting_installed``: as ``installed``, but ended up causing a solving
        # #     conflict so their pinning was relaxed to allow the solver to find a solution.
        # # * ``history``: packages that were installed and requested explicitly by the user.
        # #     These packages are pinned to a specific expression (``numpy>=1.9``).
        # #     More than one package can fulfill that expression.
        # # * ``neutered``: packages that were in the history but ended up causing a solving
        # #     conflict, so the expression was _neutered_ (relaxed); e.g. ``numpy>=1.9``
        # #     became ``numpy``. These packages could be labeled as ``conflicting_history``
        # #     but they get special treatment because they end up in the history file.
        # # * ``requested``: requested by the user explicitly in the command-line.
        # # * ``update_modifier``: added due to non-default update behavior (e.g. ``--update-all``
        # #     will add all the installed packages as bare specs with no version restrain).
        # # * ``deps_modifier``: added due to non-default dependency solving behaviour (e.g.
        # #     ``--update-deps`` will ask for a 2nd solve and add all dependencies involved in the
        # #     1st solve as marked for update even if the first solve was successful already).
        # # * ``virtual_system``: added implicitly by us so the solver can consider constrains such
        # #     as ``__glibc>=2.17``.

        # # In most conditions, ``requested`` takes precedence over everything else (especially if
        # # the user specified a version constraint, and not just a package name). Constrained specs
        # # might be relaxed if they are found to cause solver conflicts.

        # /ignore

        self.specs: Mapping[str, MatchSpec] = TrackedMap("specs", data=(specs or {}))
        self.records: Mapping[str, PackageRecord] = TrackedMap("records", data=(records or {}))
        self.neutered: Mapping[str, MatchSpec] = TrackedMap("neutered", data=(neutered or {}))

        # we track conflicts to relax some constrains and help the solver out
        self.conflicts: Mapping[str, MatchSpec] = TrackedMap("conflicts", data=(conflicts or {}))

        self.solver_input_state = solver_input_state

    @classmethod
    def from_solver_input_state(
        cls: "SolverOutputState",
        in_state: SolverInputState,
        specs: Optional[Mapping[str, MatchSpec]] = None,
        records: Optional[Mapping[str, PackageRecord]] = None,
        neutered: Optional[Mapping[str, MatchSpec]] = None,
        conflicts: Optional[Mapping[str, MatchSpec]] = None,
    ) -> "SolverOutputState":
        if records is None:
            # Pre-initialize solution to the current state of the prefix
            records = TrackedMap("records", data=in_state.installed, reason="As installed")

        inst = cls(specs=specs, records=records, conflicts=conflicts, neutered=neutered, solver_input_state=in_state)

        # Initialize specs following conda.core.solve._collect_all_metadata()

        # First initialization depends on whether we have a history to work with or not
        if in_state.history:
            # add in historically-requested specs
            inst.specs.update(in_state.history, reason="As in history")
            for name, record in in_state.installed.items():
                if name in in_state.aggressive_updates:
                    inst.specs.set(name, MatchSpec(name), reason="Installed and in aggressive updates")
                elif name in in_state.do_not_remove:
                    # these are things that we want to keep even if they're not explicitly specified.  This
                    # is to compensate for older installers not recording these appropriately for them
                    # to be preserved.
                    inst.specs.set(name, MatchSpec(name), reason="Installed and protected in do_not_remove", overwrite=False)
                elif record.subdir == "pypi":
                    # add in foreign stuff (e.g. from pip) into the specs
                    # map. We add it so that it can be left alone more. This is a
                    # declaration that it is manually installed, much like the
                    # history map. It may still be replaced if it is in conflict,
                    # but it is not just an indirect dep that can be pruned.
                    inst.specs.set(name, MatchSpec(name), reason="Installed from PyPI; protect from indirect pruning")
        else:
            # add everything in prefix if we have no history to work with (e.g. with --update-all)
            inst.specs.update({name: MatchSpec(name) for name in in_state.installed}, reason="Installed and no history available")

        # Add virtual packages so they are taken into account by the solver
        for name in in_state.virtual:
            # we only add a bare name spec here, no constrain!
            inst.specs.set(name, MatchSpec(name), reason="Virtual system", overwrite=False)

        return inst

    def prepare_for_add(self) -> dict[str, MatchSpec]:
        if self.solver_input_state is None:
            raise ValueError("Class needs to be initialized with `solver_input_state` to use this method.")

        sis = self.solver_input_state

        # The constructor should have prepared the _basics_ of the specs / records maps. Now we
        # we will try to refine the version constrains to minimize changes in the environment whenever
        # possible. Take into account this is done iteratively together with the solver! self.records
        # starts with the initial prefix state (if any), but acumulates solution attempts after each retry.

        ### Refine specs that match currently proposed solution (either prefix as is, or a failed attempt) ###

        # First, let's see if the current specs are compatible with the current records. They should be unless
        # something is very wrong with the prefix.

        for name, spec in self.specs.items():
            record_matches = [record for record in self.records.values() if spec.match(record)]

            if not record_matches:
                continue  # nothing to refine

            if len(record_matches) != 1:  # something is very wrong!
                self._raise_incompatible_spec_records(spec, record_matches)

            # ok, now we can start refining
            record = record_matches[0]
            if record.is_unmanageable:
                self.specs.set(name, record.to_match_spec(), reason="Spec matches unmanageable record")
            elif name in sis.aggressive_updates:
                self.specs.set(name, MatchSpec(name), reason="Spec matches record in aggressive updates")
            # elif name not in self.conflicts and (name not in explicit_pool or record in explicit_pool[name]):
            #     self.specs.set(name, record.to_match_spec(), reason="Spec matches record in explicit pool for its name")
            elif name in sis.history:
                # if the package was historically requested, we will honor that, but trying to
                # keep the package as installed
                # TODO: JRG: I don't know how mamba will handle _both_ a constrain and a target; play with priorities?
                self.specs.set(name, MatchSpec(sis.history[name], target=record.dist_str()), reason="Spec matches record in history")
            else:
                # every other spec that matches something installed will be configured with only a target
                # This is the case for conflicts, among others
                self.specs.set(name, MatchSpec(name, target=record.dist_str()), reason="Spec matches record")

        ### Pinnings ###

        # Now let's add the pinnings
        pin_overrides = set()
        for name, spec in sis.pinned.items():
            if name not in sis.requested:
                self.specs.set(name, MatchSpec(spec, optional=False), reason="Pinned and not explicitly requested")
            elif sis.explicit_pool[name] & sis.package_pool([spec]).get(name, set()):
                self.specs.set(name, MatchSpec(spec, optional=False), reason="Pinned and in explicitly pool")
                pin_overrides.add(name)
            else:
                self._logger.warn("pinned spec %s conflicts with explicit specs. Overriding pinned spec.", spec)


        ### Update modifiers ###

        if sis.with_freeze_installed:
            for name, record in sis.installed.items():
                if name in self.conflicts:
                    # TODO: Investigate why we use to_match_spec() here and other targets use dist_str()
                    self.specs.set(name, MatchSpec(name, target=record.to_match_spec(), optional=True), reason="Relaxing installed because it caused a conflict")
                else:
                    self.specs.set(name, record.to_match_spec(), reason="Freezing as installed")

        elif sis.with_update_all:
            # NOTE: This logic is VERY similar to what we are doing in the class constructor (?)
            if sis.history:
                # history is preferable because it has explicitly installed stuff in it.
                # that simplifies our solution.
                new = TrackedMap("new_specs")
                for name, spec in sis.history.items():
                    if name in sis.pinned:
                        new.set(name, self.specs[name], reason="Update all, with history, pinned: reusing existing entry")
                    else:
                        new.set(name, MatchSpec(spec), reason="Update all, with history, not pinned: adding spec from history with no constraints")

                for name, record in sis.installed.items():
                    if record.subdir == "pypi":
                        new.set(name, MatchSpec(name), reason="Update all, with history: treat pip installed stuff as explicitly installed")
            else:
                new = TrackedMap("new_specs")
                for name, record in sis.installed.items():
                    if name in sis.pinned:
                        new.set(name, self.specs[name], reason="Update all, no history, pinned: reusing existing entry")
                    else:
                        new.set(name, MatchSpec(name), reason="Update all, no history, not pinned: adding spec from installed with no constraints")

            # NOTE: we are REDEFINING the specs acumulated so far
            self.specs.clear()
            self.specs.update(new)

        elif sis.with_update_specs:  # this is the default behaviour if no flags are passed
            # NOTE: This _anticipates_ conflicts; we can also wait for the next attempt and
            # get the real solver conflicts as part of self.conflicts -- that would simplify
            # this logic a bit

            # ensure that our self.specs_to_add are not being held back by packages in the env.
            # This factors in pins and also ignores specs from the history.  It is unfreezing only
            # for the indirect specs that otherwise conflict with update of the immediate request
            pinned_requests = []
            for name, spec in sis.requested:
                if name not in pin_overrides and name in sis.pinned:
                    continue
                if name in sis.history:
                    continue
                pinned_requests.append(sis.package_has_updates(spec))  # needs to be implemented, requires installed pool
            conflicts = sis.get_conflicting_specs(self.specs.values(), pinned_requests) or ()
            for conflict in conflicts:
                name = conflict.name
                if name in self.specs and (name not in sis.pinned) and name not in sis.history:
                    self.specs.set(name, MatchSpec(name), reason="Relaxed because conflicting")


        ### Python pinning ###

        # As a business rule, we never want to update python beyond the current minor version,
        # unless that's requested explicitly by the user (which we actively discourage).

        if "python" in self.records and "python" not in sis.requested:
            record = self.records["python"]
            if "python" not in self.conflicts and sis.with_freeze_installed:
                self.specs.set("python", record.to_match_spec(), reason="Freezing python due to business rule, freeze-installed, and no conflicts")
            else:
                # will our prefix record conflict with any explict spec?  If so, don't add
                # anything here - let python float when it hasn't been explicitly specified
                spec = self.specs.get("python", MatchSpec("python"))
                if spec.get("version"):
                    reason = "Leaving Python pinning as it was calculated so far"
                else:
                    reason = "Pinning Python to match installed version"
                    version = get_major_minor_version(record.version) + ".*"
                    spec = MatchSpec(spec, version=version)

                # There's a chance the selected version results in a conflict -- detect and report?
                specs = (spec, ) + tuple(sis.requested.values())
                if sis.get_conflicting_specs(specs, sis.requested.values()):
                    if not sis.installing:  # TODO: repodata checks?
                        # raises a hopefully helpful error message
                        sis.find_conflicts(specs)  # this might call the solver -- remove?
                    else:
                        # oops, no message?
                        raise RawStrUnsatisfiableError("Couldn't find a Python version that does not conflict...")

                self.specs.set("python", spec, reason=reason)


        ### Offline and aggressive updates ###

        # For the aggressive_update_packages configuration parameter, we strip any target
        # that's been set.

        if not context.offline:
            for name, spec in sis.aggressive_updates:
                if name in self.specs:
                    self.specs.set(name, spec, reason="Aggressive updates relaxation")

        ### User requested specs ###

        # add in explicitly requested specs from specs_to_add
        # this overrides any name-matching spec already in the spec map

        for name, spec in sis.requested:
            if name not in pin_overrides:
                self.specs.set(name, spec, reason="Explicitly requested by user")

        ### Conda pinning ###

        # As a business rule, we never want to downgrade conda below the current version,
        # unless that's requested explicitly by the user (which we actively discourage).

        if "conda" in self.specs and paths_equal(sis.prefix, context.conda_prefix) and "conda" in sis.installed:
            record = sis.installed["conda"]
            spec = self.specs["conda"]
            required_version = f">={record.version}"
            if not spec.get("version"):
                spec = MatchSpec(spec, version=required_version)
                reason = "Pinning conda with version greater than currently installed"
            if context.auto_update_conda and "conda" not in sis.requested:
                spec = MatchSpec("conda", version=required_version, target=None)
                reason = "Pinning conda with version greater than currently installed, auto update"
            self.specs.set("conda", spec, reason=reason)

        ### Extra logic ###
        # this is where we are adding workarounds for mamba difference's in behavior, which might not belong
        # here as they are solver specific

        # next step -> .prepare_for_solve()


    def prepare_for_remove(self) -> dict[str, MatchSpec]:
        pass


    def prepare_for_solve(self):
        ### Inconsistency analysis ###
        # here we would call conda.core.solve.classic.Solver._find_inconsistent_packages()

        ### Conflict minimization ###
        # here conda.core.solve.classic.Solver._run_sat() enters a `while conflicting_specs`
        # loop to neuter some of the specs in self.specs. In other solvers we let the solver run into them.
        # We might need to add a hook here ?

        # After this, we finally let the solver do its work. It will either finish with a final state
        # or fail and repopulate the conflicts list in the SolverOutputState object
        ...

    def post_solve(self):
        # After a solve, we still need to do some refinement

        ### Neutered ###
        # annotate overridden history specs so they are written to disk

        ### Add inconsistent packages back ###
        # direct result of the inconsistency analysis above

        ### Deps modifier ###
        # handle the different modifiers (NO_DEPS, ONLY_DEPS, UPDATE_DEPS)
        # this might mean removing different records by hand or even calling the solver a 2nd time

        ### Prune ###
        # remove orphan leaves in the graph
        ...

    @property
    def _pools(self):
        # ordered by priority (high to low)
        # note this is only an approximation
        return (
            self._explicit,
            self._hard_constrained,
            self._soft_constrained,
            self._unconstrained,
        )

    @functools.lru_cache
    def _join_pools(self, *pools):
        # First item in each list is highest priority
        data = defaultdict(list)
        for pool in pools:
            for key, value in pool.items():
                data[key].append(value)
        return data

    @property
    def _data(self):
        # we don't do this directly here to use lru_cache
        return self._join_pools(self._pools)

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        yield from self._data

    def __len__(self):
        return len(self._data)

    def pool_items(self):
        """Iterator that goes over the pool items one by one."""
        for pool in self._pools:
            for item in pool:
                yield (pool, item)


    @staticmethod
    def _raise_incompatible_spec_records(spec, records):
        raise CondaError(
            dals(
                f"""
                Conda encountered an error with your environment.  Please report an issue
                at https://github.com/conda/conda/issues.  In your report, please include
                the output of 'conda info' and 'conda list' for the active environment, along
                with the command you invoked that resulted in this error.
                pkg_name: {spec.name}
                spec: {spec}
                matches_for_spec: {dashlist(records, indent=4)}
                """
            )
        )
