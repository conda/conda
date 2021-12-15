import os
from itertools import chain
from collections import defaultdict, OrderedDict
from logging import getLogger
from tempfile import NamedTemporaryFile
from typing import Iterable, Mapping, Optional

from ...base.constants import REPODATA_FN, ChannelPriority
from ...base.context import context
from ...common.constants import NULL
from ...common.serialize import json_dump
from ...common.url import (
    escape_channel_url,
    split_anaconda_token,
    remove_auth,
)
from ...exceptions import (
    PackagesNotFoundError,
    RawStrUnsatisfiableError,
)
from ...models.channel import Channel
from ...models.match_spec import MatchSpec
from .classic import Solver
from .state import SolverInputState, SolverOutputState


log = getLogger(__name__)


class LibMambaSolver2(Solver):
    """
    Cleaner implementation using the ``state`` module helpers.
    """
    def __init__(
        self,
        prefix,
        channels,
        subdirs=(),
        specs_to_add=(),
        specs_to_remove=(),
        repodata_fn=REPODATA_FN,
        command=NULL,
     ):
        if specs_to_add and specs_to_remove:
            raise ValueError("Only one of `specs_to_add` and `specs_to_remove` can be set at a time")

        super().__init__(
            prefix,
            channels,
            subdirs=subdirs,
            specs_to_add=specs_to_add,
            specs_to_remove=specs_to_remove,
            repodata_fn=repodata_fn,
            command=command
        )

        if self.subdirs is NULL or not self.subdirs:
            self.subdirs = context.subdirs

        # These two attributes are set during ._setup_solver()
        self.solver = None
        self._index = None

    def solve_final_state(self,
        update_modifier=NULL,
        deps_modifier=NULL,
        prune=NULL,
        ignore_pinned=NULL,
        force_remove=NULL,
        should_retry_solve=False,
    ):
        if not context.json and not context.quiet:
            print("------ USING EXPERIMENTAL LIBMAMBA2 INTEGRATIONS ------")

        in_state = SolverInputState(
            prefix=self.prefix,
            requested=self.specs_to_add or self.specs_to_remove,
            update_modifier=update_modifier,
            deps_modifier=deps_modifier,
            prune=prune,
            ignore_pinned=ignore_pinned,
            force_remove=force_remove,
        )

        out_state = SolverOutputState(solver_input_state=in_state)

        # These tasks do _not_ require a solver...
        # TODO: Abstract away in the base class?
        none_or_final_state = out_state.early_exit()
        if none_or_final_state is not None:
            return none_or_final_state

        # From now on we _do_ require a solver
        self._setup_solver(in_state)

        attempts = 0
        while attempts <= len(in_state.installed):
            attempts += 1
            log.debug("Starting solver attempt %s", attempts)
            solved = self._solve_attempt(in_state, out_state)
            if solved:
                break

        log.debug("Last attempt: reporting all installed as conflicts")
        out_state.conflicts.update(
            {
                name: record.to_match_spec()
                for name, record in in_state.installed.items()
                if not record.is_unmanageable
            },
            reason="Last attempt: all installed packages exposed as conflicts for maximum flexibility"
        )
        solved = self._solve_attempt(in_state, out_state)
        if not solved:
            # If we haven't found a solution already, we failed...
            self._raise_for_problems()

        # We didn't fail? Nice, let's return the calculated state
        self._get_solved_records(in_state, out_state)

        # Run post-solve tasks
        out_state.post_solve(solver_cls=self.__class__)

        return out_state.current_solution

    def _setup_solver(self, in_state: SolverInputState):
        if self.solver is not None:
            return

        import libmambapy as api
        from .libmamba_utils import load_channels, init_api_context

        init_api_context()

        # We don't really use the pool again, but we need to keep a
        # non-local reference to the object in the Python layer so
        # we don't get segfaults due to the missing object down the line
        self._pool = pool = api.Pool()

        # export installed records to a temporary json file
        exported_installed = {"packages": {}}
        for record in chain(in_state.installed.values(), in_state.virtual.values()):
            exported_installed["packages"][record.fn] = {
                **record.dist_fields_dump(),
                "depends": record.depends,
                "constrains": record.constrains,
                "build": record.build,
            }
        with NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write(json_dump(exported_installed))
        installed = api.Repo(pool, "installed", f.name, "")
        installed.set_installed()
        os.unlink(f.name)

        self._index = load_channels(
            pool=pool,
            channels=self._channel_urls(),
            repos=[installed],
            prepend=False,
            use_local=context.use_local,
            platform=self.subdirs
        )

        solver_options = [(api.SOLVER_FLAG_ALLOW_DOWNGRADE, 1)]
        if self._command == "remove":
            solver_options.append((api.SOLVER_FLAG_ALLOW_UNINSTALL, 1))
        if context.channel_priority is ChannelPriority.STRICT:
            solver_options.append((api.SOLVER_FLAG_STRICT_REPO_PRIORITY, 1))

        self.solver = api.Solver(pool, solver_options)

    def _channel_urls(self):
        """
        TODO: libmambapy could handle path to url, and escaping
        but so far we are doing it ourselves
        """
        def _channel_to_url_or_name(channel):
            # This fixes test_activate_deactivate_modify_path_bash
            # and other local channels (path to url) issues
            urls = []
            for url in channel.urls():
                url = url.rstrip("/").rsplit("/", 1)[0]  # remove subdir
                urls.append(escape_channel_url(url))
            # deduplicate
            urls = list(OrderedDict.fromkeys(urls))
            return urls

        channels = [url for c in self._channels for url in _channel_to_url_or_name(Channel(c))]
        if context.restore_free_channel and "https://repo.anaconda.com/pkgs/free" not in channels:
            channels.append('https://repo.anaconda.com/pkgs/free')

        return tuple(channels)

    def _solve_attempt(self, in_state: SolverInputState, out_state: SolverOutputState):
        if self.solver is None:
            raise RuntimeError("Solver is not initialized. Call `._setup_solver()` first.")

        log.debug("New solver attempt")
        log.debug("Current conflicts (including learnt ones): %s", out_state.conflicts)

        ### First, we need to obtain the list of specs ###
        out_state.prepare_specs()
        log.debug("Computed specs: %s", out_state.specs)

        ### Conver to tasks
        tasks = self._specs_to_tasks(in_state, out_state)
        for (task_name, task_type), specs in tasks.items():
            log.debug("Adding task %s with specs %s", task_name, specs)
            self.solver.add_jobs(specs, task_type)

        ### Run solver
        solved = self.solver.solve()
        if solved:
            out_state.conflicts.clear(reason="Solution found")
            return solved

        problems = self.solver.problems_to_str()
        old_conflicts = out_state.conflicts.copy()
        new_conflicts = self._problems_to_specs(problems, old_conflicts)
        out_state.conflicts.update(new_conflicts.items(), reason="New conflict found")
        log.debug("Attempt failed with %s conflicts", len(new_conflicts))
        return False

    def _specs_to_tasks(self, in_state: SolverInputState, out_state: SolverOutputState):
        log.debug("Creating tasks for %s specs", len(out_state.specs))
        if in_state.is_removing:
            return self._specs_to_tasks_remove(in_state, out_state)
        return self._specs_to_tasks_add(in_state, out_state)

    def _specs_to_tasks_add(self, in_state: SolverInputState, out_state: SolverOutputState):
        import libmambapy as api

        tasks = defaultdict(list)
        for name, spec in out_state.specs.items():
            spec = spec.conda_build_form()
            if name.startswith("__"):
                continue
            ### Low-prio task ###
            if name in out_state.conflicts:
                if name in in_state.installed or name in ("python", "conda"):
                    continue
                tasks[("DISFAVOR", api.SOLVER_DISFAVOR)].append(spec)
                tasks[("ALLOWUNINSTALL", api.SOLVER_ALLOWUNINSTALL)].append(spec)
                key = "INSTALL", api.SOLVER_INSTALL

            ### Regular task ###
            elif name in in_state.installed:
                ### Protect if installed AND history
                if name in in_state.history:
                    installed_spec = in_state.installed[name].to_match_spec().conda_build_form()
                    tasks[("USERINSTALLED", api.SOLVER_USERINSTALLED)].append(installed_spec)
                # In addition to that, install or update it
                if name in ("python", "conda"):
                    key = ("UPDATE | ESSENTIAL", api.SOLVER_UPDATE | api.SOLVER_ESSENTIAL)
                else:
                    key = "UPDATE", api.SOLVER_UPDATE
            else:
                key = "INSTALL", api.SOLVER_INSTALL

            tasks[key].append(spec)

        tasks_list_as_str = "  \n".join(
            [f"{task_str}: {', '.join(specs)}"
             for (task_str, _), specs in tasks.items()]
        )
        log.debug("Created %s tasks:\n  %s", len(tasks), tasks_list_as_str)

        return tasks

    def _specs_to_tasks_remove(self, in_state: SolverInputState, out_state: SolverOutputState):
        # TODO: Consider merging add/remove in a single logic this so there's no split
        import libmambapy as api

        tasks = defaultdict(list)

        # Protect history and aggressive updates from being uninstalled if possible
        for name, spec in out_state.specs.items():
            spec = spec.conda_build_form()
            aggressive_update = name in in_state.aggressive_updates and name in in_state.installed
            if name in in_state.history and aggressive_update:
                tasks[("USERINSTALLED", api.SOLVER_USERINSTALLED)].append(spec)

        # No complications here: delete requested and their deps
        # TODO: There are some flags to take care of here, namely:
        # --all
        # --no-deps
        # --deps-only
        key = ("ERASE | CLEANDEPS", api.SOLVER_ERASE | api.SOLVER_CLEANDEPS)
        for name, spec in in_state.requested.items():
            spec.conda_build_form()
            tasks[key].append(spec)

        return tasks

    def _problems_to_specs(self, problems: str, previous: Mapping[str, MatchSpec]):
        if self.solver is None:
            raise RuntimeError("Solver is not initialized. Call `._setup_solver()` first.")

        dashed_specs = []       # e.g. package-1.2.3-h5487548_0
        conda_build_specs = []  # e.g. package 1.2.8.*
        missing = []
        for line in problems.splitlines():
            line = line.strip()
            words = line.split()
            if not line.startswith("- "):
                continue
            if "none of the providers can be installed" in line:
                assert words[1] == "package"
                assert words[3] == "requires"
                dashed_specs.append(words[2])
                end = words.index("but")
                conda_build_specs.append(words[4:end])
            elif "- nothing provides" in line and "needed by" in line:
                missing.append(words[-1])
                dashed_specs.append(words[-1])
            elif "- nothing provides" in line:
                missing.append(words[4:])
                conda_build_specs.append(words[4:])

        conflicts = {}
        for conflict in dashed_specs:
            name, version, build = conflict.rsplit("-", 2)
            conflicts[name] = MatchSpec(name=name, version=version, build=build)
            conflicts[name].missing = conflict in missing  # TODO: FIX this ugly hack
        for conflict in conda_build_specs:
            kwargs = {"name": conflict[0].rstrip(",")}
            if len(conflict) >= 2:
                kwargs["version"] = conflict[1].rstrip(",")
            if len(conflict) == 3:
                kwargs["build"] = conflict[2].rstrip(",")
            conflicts[kwargs["name"]] = MatchSpec(**kwargs)
            conflicts[kwargs["name"]].missing = conflict in missing

        previous_set = set(previous.values())
        current_set = set(conflicts.values())

        diff = current_set.difference(previous_set)
        if len(diff) > 1 and "python" in conflicts:
            # Only report python as conflict if it's the only conflict reported
            # This helps us prioritize neutering for other dependencies first
            conflicts.pop("python")

        current_set = set(conflicts.values())
        if (previous and (previous_set == current_set)) or len(diff) >= 10:
            # We have same or more (up to 10) conflicts now! Abort to avoid recursion.
            self._raise_for_problems(problems)

        return conflicts

    def _raise_for_problems(self, problems: Optional[str] = None):
        if self.solver is None:
            raise RuntimeError("Solver is not initialized. Call `._setup_solver()` first.")

        # TODO: merge this with parse_problems somehow
        # e.g. return a dict of exception type -> specs involved
        # and we raise it here
        if problems is None:
            problems = self.solver.problems_to_str()

        for line in problems.splitlines():
            line = line.strip()
            if line.startswith("- nothing provides requested"):
                packages = line.split()[4:]
                raise PackagesNotFoundError([" ".join(packages)])
        raise RawStrUnsatisfiableError(problems)

    def _get_solved_records(self, in_state: SolverInputState, out_state: SolverOutputState):
        if self.solver is None:
            raise RuntimeError("Solver is not initialized. Call `._setup_solver()` first.")

        import libmambapy as api
        from .libmamba_utils import to_package_record_from_subjson

        transaction = api.Transaction(self.solver, api.MultiPackageCache(context.pkgs_dirs))
        (names_to_add, names_to_remove), to_link, to_unlink = transaction.to_conda()

        channel_lookup = {}
        for _, entry in self._index:
            key = entry["channel"].platform_url(entry["platform"], with_credentials=False)
            channel_lookup[key] = entry

        for _, filename in to_unlink:
            for name, record in in_state.installed.items():
                if record.is_unmanageable:
                    # ^ Do not try to unlink virtual pkgs, virtual eggs, etc
                    continue
                if record.fn == filename:  # match!
                    out_state.records.pop(name, None, reason="Unlinked by solver")
                    break
            else:
                log.warn("Tried to unlink %s but it is not installed or manageable?", filename)

        for channel, filename, json_str in to_link:
            if channel.startswith("file://"):
                # The conda functions (specifically remove_auth) assume the input
                # is a url; a file uri on windows with a drive letter messes them up.
                key = channel
            else:
                key = split_anaconda_token(remove_auth(channel))[0]
            if key not in channel_lookup:
                raise ValueError(f"missing key {key} in channels {channel_lookup}")
            record = to_package_record_from_subjson(channel_lookup[key], filename, json_str)
            out_state.records.set(record.name, record, reason="Part of solution calculated by libmamba")

    def _reset(self):
        self.solver = None
        self._index = None
