"""
Solver-agnostic logic to expose the prefix state to the solver.
"""

from collections import defaultdict, MutableMapping
from itertools import chain
from types import MappingProxyType
from typing import Any, Hashable, Iterable, Type, Union, Optional, Tuple, Mapping
from os import PathLike
import logging
import functools

from ... import CondaError
from ..._vendor.boltons.setutils import IndexedSet
from ...auxlib import NULL
from ...auxlib.ish import dals
from ...base.constants import DepsModifier, UpdateModifier
from ...base.context import context
from ...common.io import dashlist
from ...common.path import get_major_minor_version, paths_equal
from ...exceptions import (
    PackagesNotFoundError,
    RawStrUnsatisfiableError,
    SpecsConfigurationConflictError
)
from ...history import History
from ...models.channel import Channel
from ...models.match_spec import MatchSpec
from ...models.records import PackageRecord
from ...models.prefix_graph import PrefixGraph
from ..index import _supplement_index_with_system
from ..prefix_data import PrefixData
from .classic import get_pinned_specs

logger = logging.getLogger(__name__)

class TrackedMap(MutableMapping):
    # TODO: I am sure there's a better place for this object; e.g. conda.models
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
        self._clsname = self.__class__.__name__
        self._logger = logging.getLogger(__name__)

        if isinstance(data, TrackedMap):
            self._data = data._data.copy()
            if reason:
                self._reasons = {k: reason for k in self._data}
            else:
                self._reasons = data._reasons.copy()
        else:
            self._data = {}
            self._reasons = defaultdict(list)
            self.update(data or {}, reason=reason)

    def _set(self, key, value, *, reason: Optional[str] = None, overwrite=True, _level=3):
        assert isinstance(key, str), f"{key!r} is not str ({reason})"
        try:
            old = self._data[key]
            old_reason = self._reasons.get(key, [None])[-1]
            msg = (
                f"{self._clsname}:{self._name}[{key!r}] "
                f"(={old!r}, reason={old_reason}) updated to {self._short_repr(value)}"
            )
            write = overwrite
        except KeyError:
            msg = f"{self._clsname}:{self._name}[{key!r}] set to {self._short_repr(value)}"
            write = True

        if write:
            if reason:
                msg += f' (reason={reason})'
                self._reasons[key].append(reason)
            self._data[key] = value
        else:
            msg = (
                f"{self._clsname}:{self._name}[{key!r}] "
                f"(={old!r}, reason={old_reason}) wanted new value {self._short_repr(value)} "
                f"(reason={reason}) but stayed the same due to overwrite=False."
            )

        self._logger.debug(msg, stacklevel=_level)

    @property
    def name(self):
        return self._name

    def __repr__(self):
        if not self._data:
            return "{}"
        lines = ["{"]
        for k, v in self._data.items():
            reasons = self._reasons.get(k)
            reasons = f"  # reasons={reasons}" if reasons else ""
            lines.append(f"  {k!r}: {v!r},{reasons}")
        lines.append("}")
        return "\n".join(lines)

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
        self._logger.debug(f'{self._clsname}:{self._name}[{key!r}] was deleted', stacklevel=2)

    def pop(self, key: Hashable, *default: Any, reason: Optional[str] = None) -> Any:
        """
        Remove a key-value pair and return the value. A reason can be provided
        for logging purposes, but it won't be stored in the object.
        """
        value = self._data.pop(key)
        self._reasons.pop(key, *default)
        msg = f'{self._clsname}:{self._name}[{key!r}] (={self._short_repr(value)}) was deleted'
        if reason:
            msg += f" (reason={reason})"
        self._logger.debug(msg, stacklevel=2)
        return value

    def popitem(self, key: Hashable, *default: Any, reason: Optional[str] = None) -> Tuple[Hashable, Any]:
        """
        Remove and return a key-value pair. A reason can be provided for logging purposes,
        but it won't be stored in the object.
        """
        key, value = self._data.popitem(key)
        self._reasons.pop(key, *default)
        msg = f'{self._clsname}:{self._name}[{key!r}] (={self._short_repr(value)}) was deleted'
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

    def copy(self):
        return self.__class__(name=self._name, data=self)

    @staticmethod
    def _short_repr(value, maxlen=100):
        value_repr = repr(value)
        if len(value_repr) > maxlen:
            value_repr = f"{value_repr[:maxlen-4]}...>"
        return value_repr
class IndexState:
    """
    The _index_ refers to the combination of all configured channels and their
    platform-corresponding subdirectories. It provides the sources for available
    packages that can become part of a prefix state, eventually.
    """

    def __init__(
        self,
        channels: Optional[Iterable[Union[str, Channel]]] = None,
        subdirs: Optional[Iterable[str]] = None,
    ):
        self.channels = tuple(Channel(c) for c in (channels or context.channels))
        self.subdirs = tuple(subdir for subdir in (subdirs or context.subdirs))


class SolverInputState:
    # TODO: I am sure there's a better place for this object; e.g. conda.models

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
    _ENUM_STR_MAP = {
            "NOT_SET": DepsModifier.NOT_SET,
            "NO_DEPS": DepsModifier.NO_DEPS,
            "ONLY_DEPS": DepsModifier.ONLY_DEPS,
            "SPECS_SATISFIED_SKIP_SOLVE": UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE,
            "FREEZE_INSTALLED": UpdateModifier.FREEZE_INSTALLED,
            "UPDATE_DEPS": UpdateModifier.UPDATE_DEPS,
            "UPDATE_SPECS": UpdateModifier.UPDATE_SPECS,
            "UPDATE_ALL": UpdateModifier.UPDATE_ALL,
    }
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
        self.prefix = prefix
        self._prefix_data = PrefixData(prefix, pip_interop_enabled=_pip_interop_enabled)
        self._pip_interop_enabled = _pip_interop_enabled
        self._history = History(prefix).get_requested_specs_map()
        self._pinned = {spec.name: spec for spec in get_pinned_specs(prefix)}
        self._aggressive_updates = {spec.name: spec for spec in context.aggressive_update_packages}

        virtual = {}
        _supplement_index_with_system(virtual)
        self._virtual = {record.name: record for record in virtual}

        self._requested = {}
        for spec in requested:
            spec = MatchSpec(spec)
            self._requested[spec.name] = spec

        self._update_modifier = self._value_from_context_if_null("update_modifier", update_modifier)
        self._deps_modifier = self._value_from_context_if_null("deps_modifier", deps_modifier)
        self._ignore_pinned = self._value_from_context_if_null("ignore_pinned", ignore_pinned)
        self._force_remove = self._value_from_context_if_null("force_remove", force_remove)
        self._force_reinstall = self._value_from_context_if_null("force_reinstall", force_reinstall)
        self._prune = prune
        self._command = command

        # special cases
        _do_not_remove = ('anaconda', 'conda', 'conda-build', 'python.app', 'console_shortcut', 'powershell_shortcut')
        self._do_not_remove = {p: MatchSpec(p) for p in _do_not_remove}

        self._check_state()

    def _check_state(self):
        """
        Run some consistency checks to ensure configuration is solid.
        """
        # Ensure configured pins match installed builds
        for name, spec in self._pinned.items():
            installed = self.installed.get(name)
            if installed:
                if not spec.match(installed):
                    raise SpecsConfigurationConflictError([installed], [spec], self.prefix)

    def _value_from_context_if_null(self, name, value, context=context):
        return getattr(context, name) if value is NULL else self._ENUM_STR_MAP.get(value, value)

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

    ### methods
    def package_has_updates(self, *args, **kwargs):
        logger.warning("Method `package_has_updates` not implemented!")
        return ()

    def get_conflicting_specs(self, *args, **kwargs):
        logger.warning("Method `get_conflicting_specs` not implemented!")
        return ()


class SolverOutputState(Mapping):
    # TODO: This object is starting to look _a lot_ like conda.core.solve itself...
    # Consider merging this with a base class in conda.core.solve
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
        solver_input_state: SolverInputState,
        specs: Optional[Mapping[str, MatchSpec]] = None,
        records: Optional[Mapping[str, PackageRecord]] = None,
        for_history: Optional[Mapping[str, MatchSpec]] = None,
        neutered: Optional[Mapping[str, MatchSpec]] = None,
        conflicts: Optional[Mapping[str, MatchSpec]] = None,
    ):
        self.solver_input_state: SolverInputState = solver_input_state

        self.records: Mapping[str, PackageRecord] = TrackedMap("records")
        if records:
            self.records.update(records, reason="Initialized from explicitly passed arguments")
        elif solver_input_state.installed:
            self.records.update(solver_input_state.installed, reason="Initialized from installed packages in prefix")

        self.specs: Mapping[str, MatchSpec] = TrackedMap("specs")
        if specs:
            self.specs.update(specs, reason="Initialized from explicitly passed arguments")
        else:
            self._initialize_specs_from_input_state()

        self.for_history: Mapping[str, MatchSpec] = TrackedMap("for_history")
        if for_history:
            self.for_history.update(for_history, reason="Initialized from explicitly passed arguments")
        elif solver_input_state.requested:
            self.for_history.update(solver_input_state.requested, reason="Initialized from requested specs in solver input state")

        self.neutered: Mapping[str, MatchSpec] = TrackedMap("neutered", data=(neutered or {}), reason="From arguments")

        # we track conflicts to relax some constrains and help the solver out
        self.conflicts: Mapping[str, MatchSpec] = TrackedMap("conflicts", data=(conflicts or {}), reason="From arguments")


    def _initialize_specs_from_input_state(self):
        # Initialize specs following conda.core.solve._collect_all_metadata()

        # First initialization depends on whether we have a history to work with or not
        if self.solver_input_state.history:
            # add in historically-requested specs
            self.specs.update(self.solver_input_state.history, reason="As in history")
            for name, record in self.solver_input_state.installed.items():
                if name in self.solver_input_state.aggressive_updates:
                    self.specs.set(name, MatchSpec(name), reason="Installed and in aggressive updates")
                elif name in self.solver_input_state.do_not_remove:
                    # these are things that we want to keep even if they're not explicitly specified.  This
                    # is to compensate for older installers not recording these appropriately for them
                    # to be preserved.
                    self.specs.set(name, MatchSpec(name), reason="Installed and protected in do_not_remove", overwrite=False)
                elif record.subdir == "pypi":
                    # add in foreign stuff (e.g. from pip) into the specs
                    # map. We add it so that it can be left alone more. This is a
                    # declaration that it is manually installed, much like the
                    # history map. It may still be replaced if it is in conflict,
                    # but it is not just an indirect dep that can be pruned.
                    self.specs.set(name, MatchSpec(name), reason="Installed from PyPI; protect from indirect pruning")
        else:
            # add everything in prefix if we have no history to work with (e.g. with --update-all)
            self.specs.update({name: MatchSpec(name) for name in self.solver_input_state.installed}, reason="Installed and no history available")

        # Add virtual packages so they are taken into account by the solver
        for name in self.solver_input_state.virtual:
            # we only add a bare name spec here, no constrain!
            self.specs.set(name, MatchSpec(name), reason="Virtual system", overwrite=False)

    @property
    def current_solution(self):
        return IndexedSet(PrefixGraph(self.records.values()).graph)

    def prepare_specs(self) -> Mapping[str, MatchSpec]:
        if self.solver_input_state.is_removing:
            self._prepare_for_remove()
        else:
            self._prepare_for_add()
        self._prepare_for_solve()
        return self.specs

    def _prepare_for_add(self) -> Mapping[str, MatchSpec]:
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
            elif name not in self.conflicts: # TODO: and (name not in explicit_pool or record in explicit_pool[name]):
                self.specs.set(name, record.to_match_spec(), reason="Spec matches record in explicit pool for its name")
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
            # NOTE: we are REDEFINING the specs acumulated so far
            self.specs.clear(reason="Redefining from scratch due to --update-all")
            if sis.history:
                # history is preferable because it has explicitly installed stuff in it.
                # that simplifies our solution.
                for name in sis.history:
                    if name in sis.pinned:
                        self.specs.set(name, self.specs[name], reason="Update all, with history, pinned: reusing existing entry")
                    else:
                        self.specs.set(name, MatchSpec(name), reason="Update all, with history, not pinned: adding spec from history with no constraints")

                for name, record in sis.installed.items():
                    if record.subdir == "pypi":
                        self.specs.set(name, MatchSpec(name), reason="Update all, with history: treat pip installed stuff as explicitly installed")
            else:
                for name in sis.installed:
                    if name in sis.pinned:
                        self.specs.set(name, self.specs[name], reason="Update all, no history, pinned: reusing existing entry")
                    else:
                        self.specs.set(name, MatchSpec(name), reason="Update all, no history, not pinned: adding spec from installed with no constraints")

        elif sis.with_update_specs:  # this is the default behaviour if no flags are passed
            # NOTE: This _anticipates_ conflicts; we can also wait for the next attempt and
            # get the real solver conflicts as part of self.conflicts -- that would simplify
            # this logic a bit

            # ensure that our self.specs_to_add are not being held back by packages in the env.
            # This factors in pins and also ignores specs from the history.  It is unfreezing only
            # for the indirect specs that otherwise conflict with update of the immediate request
            # pinned_requests = []
            # for name, spec in sis.requested.items():
            #     if name not in pin_overrides and name in sis.pinned:
            #         continue
            #     if name in sis.history:
            #         continue
            #     pinned_requests.append(sis.package_has_updates(spec))  # needs to be implemented, requires installed pool
            # conflicts = sis.get_conflicting_specs(self.specs.values(), pinned_requests) or ()
            for name in self.conflicts:
                if name not in sis.pinned and name not in sis.history and name not in sis.requested:
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
                # specs = (spec, ) + tuple(sis.requested.values())
                # if sis.get_conflicting_specs(specs, sis.requested.values()):
                #     if not sis.installing:  # TODO: repodata checks?
                #         # raises a hopefully helpful error message
                #         sis.find_conflicts(specs)  # this might call the solver -- remove?
                #     else:
                #         # oops, no message?
                #         raise RawStrUnsatisfiableError("Couldn't find a Python version that does not conflict...")

                self.specs.set("python", spec, reason=reason)


        ### Offline and aggressive updates ###

        # For the aggressive_update_packages configuration parameter, we strip any target
        # that's been set.

        if not context.offline:
            for name, spec in sis.aggressive_updates.items():
                if name in self.specs:
                    self.specs.set(name, spec, reason="Aggressive updates relaxation")

        ### User requested specs ###

        # add in explicitly requested specs from specs_to_add
        # this overrides any name-matching spec already in the spec map

        for name, spec in sis.requested.items():
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
                self.specs.set("conda", spec, reason=reason)
            if context.auto_update_conda and "conda" not in sis.requested:
                spec = MatchSpec("conda", version=required_version, target=None)
                reason = "Pinning conda with version greater than currently installed, auto update"
                self.specs.set("conda", spec, reason=reason)

        ### Extra logic ###
        # this is where we are adding workarounds for mamba difference's in behavior, which might not belong
        # here as they are solver specific

        # next step -> .prepare_for_solve()


    def _prepare_for_remove(self) -> Mapping[str, MatchSpec]:
        # This logic is simpler than when we are installing packages
        self.specs.update(self.solver_input_state.requested, reason="Adding user-requested specs")

    def _prepare_for_solve(self):
        ### Inconsistency analysis ###
        # here we would call conda.core.solve.classic.Solver._find_inconsistent_packages()

        ### Check conflicts are only present in .specs
        conflicting_and_pinned = [
            spec for name, spec in self.conflicts.items()
            if name in self.solver_input_state.pinned
        ]
        if conflicting_and_pinned:
            requested = [
                str(spec)
                for spec in chain(self.specs, self.solver_input_state.requested)
                if spec not in conflicting_and_pinned
            ]
            raise SpecsConfigurationConflictError(
                requested_specs=requested,
                pinned_specs=[str(spec) for spec in conflicting_and_pinned],
                prefix=self.solver_input_state.prefix,
            )

        ### Conflict minimization ###
        # here conda.core.solve.classic.Solver._run_sat() enters a `while conflicting_specs`
        # loop to neuter some of the specs in self.specs. In other solvers we let the solver run into them.
        # We might need to add a hook here ?

        # After this, we finally let the solver do its work. It will either finish with a final state
        # or fail and repopulate the conflicts list in the SolverOutputState object

    def early_exit(self):
        """
        Operations that do not need a solver at all and might result in returning early
        are collected here.
        """
        sis = self.solver_input_state

        if sis.is_removing and sis.force_remove:
            for name, spec in self.requested.items():
                for record in self.installed.values():
                    if spec.match(record):
                        self.records.pop(name)
                        break
            return self.current_solution

        if sis.with_specs_satisfied_skip_solve and not sis.is_removing:
            for name, spec in sis.requested.items():
                if name not in sis.installed:
                    break
            else:
                # All specs match a package in the current environment.
                # Return early, with the current solution (at this point, .records is set
                # to the map of installed packages)
                return self.current_solution

        # Check we are not trying to remove things that are not installed
        if sis.is_removing:
            not_installed = [spec for name, spec in sis.requested.items() if name not in sis.installed]
            if not_installed:
                raise PackagesNotFoundError(not_installed)

    def post_solve(self, solver: Type["Solver"]):
        """
        These tasks are performed _after_ the solver has done its work. It could be solver-agnostic
        but unfortunately ``--update-deps`` requires a second solve; that's why this method needs
        a solver class to be passed as an argument.

        Parameters
        ----------
        solver_cls
            The class used to instantiate the Solver. If not provided, defaults to the one specified
            in the context configuration.
        """
        # After a solve, we still need to do some refinement
        sis = self.solver_input_state

        ### Record history ###
        # user requested specs need to be annotated in history
        # we control that in .for_history
        self.for_history.update(sis.requested, reason="User requested specs recorded to history")

        ### Neutered ###
        # annotate overridden history specs so they are written to disk
        for name, spec in self.specs.items():
            if name in sis.history and spec.strictness < sis.history[name].strictness:
                self.neutered.set(name, spec, reason="Spec needs less strict constrains than history ")

        ### Add inconsistent packages back ###
        # direct result of the inconsistency analysis above

        ### Deps modifier ###
        # handle the different modifiers (NO_DEPS, ONLY_DEPS, UPDATE_DEPS)
        # this might mean removing different records by hand or even calling the solver a 2nd time

        if sis.with_no_deps:
            # In the NO_DEPS case, we need to start with the original list of packages in the
            # environment, and then only modify packages that match the requested specs
            #
            # Help information notes that use of NO_DEPS is expected to lead to broken
            # environments.
            original_state = dict(sis.installed)
            only_change_these = {}
            for name, spec in sis.requested.items():
                for record in self.records.values():
                    if spec.match(record):
                        only_change_these[name] = record

            if sis.is_removing:
                # TODO: This could be a pre-solve task to save time in forced removes?
                for name in only_change_these:
                    del original_state[name]
            else:
                for name, record in only_change_these.items():
                    original_state[name] = record

            self.records.clear(reason="Redefining records due to --no-deps")
            self.records.update(original_state, reason="Redefined records due to --no-deps")

        elif sis.with_only_deps and not sis.with_update_deps:
            # Using a special instance of PrefixGraph to remove youngest child nodes that match
            # the original requested specs.  It's important to remove only the *youngest* child nodes,
            # because a typical use might be `conda install --only-deps python=2 flask`, and in
            # that case we'd want to keep python.
            #
            # What are we supposed to do if flask was already in the environment?
            # We can't be removing stuff here that's already in the environment.
            #
            # What should be recorded for the user-requested specs in this case? Probably all
            # direct dependencies of flask.

            graph = PrefixGraph(self.records.values(), sis.requested.values())
            # this method below modifies the graph inplace _and_ returns the removed nodes (like dict.pop())
            would_remove = graph.remove_youngest_descendant_nodes_with_specs()

            # We need to distinguish the behaviour between `conda remove` and the rest
            if sis.is_removing:
                to_remove = []
                for record in would_remove:
                    # do not remove records that were not requested but were installed
                    if record.name not in sis.requested and record.name in sis.installed:
                        continue
                    to_remove.append(record)
            else:
                to_remove = would_remove
                for record in would_remove:
                    for dependency in record.depends:
                        spec = MatchSpec(dependency)
                        if spec.name not in self.specs:
                            # NOTE: We are REDEFINING the requested specs so they are recorded in history
                            # following https://github.com/conda/conda/pull/8766
                            # reason="Recording deps brought by --only-deps as explicit"
                            sis._requested[spec.name] = spec


            for record in to_remove:
                self.records.pop(record.name, reason="Excluding from solution due to --only-deps")

        elif sis.with_update_deps:
            # Here we have to SAT solve again :(  It's only now that we know the dependency
            # chain of specs_to_add.
            #
            # UPDATE_DEPS is effectively making each spec in the dependency chain a user-requested
            # spec. For all other specs, we drop all information but name, drop target, and add them to
            # `requested` so it gets recorded in the history file.
            #
            # It's like UPDATE_ALL, but only for certain dependency chains.
            new_specs = TrackedMap("update_deps_specs")

            graph = PrefixGraph(self.records.values())
            for name, spec in sis.requested.items():
                record = graph.get_node_by_name(name)
                for ancestor in graph.all_ancestors(record):
                    new_specs.set(ancestor.name, MatchSpec(ancestor.name), reason="New specs asked by --update-deps")

            # Remove pinned_specs
            for name, spec in sis.pinned.items():
                new_specs.pop(name, None, reason="Exclude pinned packages from --update-deps specs")
            # Follow major-minor pinning business rule for python
            if "python" in new_specs:
                record = sis.installed["python"]
                version = ".".join(record.version.split(".")[:2]) + ".*"
                new_specs.set("python", MatchSpec(name="python", version=version))
            # Add in the original `requested` on top.
            new_specs.update(sis.requested, reason="Add original requested specs on top for --update-deps")

            if sis.is_removing:
                specs_to_add = ()
                specs_to_remove = new_specs
            else:
                specs_to_add = list(new_specs.values())
                specs_to_remove = ()

            with context.override("quiet", True):
                # Create a new solver instance to perform a 2nd solve with deps added
                # We do it like this to avoid overwriting state accidentally. Instead,
                # we will import the needed state bits manually.
                records = solver.__class__(
                    prefix=solver.prefix,
                    channels=solver.channels,
                    subdirs=solver.subdirs,
                    specs_to_add=specs_to_add,
                    specs_to_remove=specs_to_remove,
                    command="recursive_call_for_update_deps"
                ).solve_final_state(
                    update_modifier=UpdateModifier.UPDATE_SPECS,  # avoid recursion!
                    deps_modifier=sis.deps_modifier,
                    ignore_pinned=sis.ignore_pinned,
                    force_remove=sis.force_remove,
                    prune=sis.prune
                )
                records = {record.name: record for record in records}

            self.records.clear(reason="Redefining due to --update-deps")
            self.records.update(records, reason="Redefined due to --update-deps")
            self.for_history.clear(reason="Redefining due to --update-deps")
            self.for_history.update(new_specs, reason="Redefined due to --update-deps")

            # Disable pruning regardless the original value
            # TODO: Why? Dive in https://github.com/conda/conda/pull/7719
            sis._prune = False

        ### Prune ###
        # remove orphan leaves in the graph
        if sis.prune:
            graph = PrefixGraph(list(self.records.values()), self.specs.values())
            graph.prune()
            self.records.clear(reason="Pruning")
            self.records.update({record.name: record for record in graph.graph}, reason="Pruned")

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

    @functools.lru_cache(maxsize=None)
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
