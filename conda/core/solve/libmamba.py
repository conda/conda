
from itertools import chain
from collections import defaultdict, OrderedDict
from logging import getLogger

from ..index import _supplement_index_with_system
from ..prefix_data import PrefixData
from ... import CondaError
from ..._vendor.boltons.setutils import IndexedSet
from ..._vendor.toolz import concatv, groupby
from ...base.constants import DepsModifier, UpdateModifier, ChannelPriority
from ...base.context import context
from ...common.constants import NULL
from ...common.path import get_major_minor_version, paths_equal
from ...common.url import (
    escape_channel_url,
    split_anaconda_token,
    remove_auth,
)
from ...exceptions import (
    PackagesNotFoundError,
    SpecsConfigurationConflictError,
    RawStrUnsatisfiableError,
)
from ...history import History
from ...models.channel import Channel
from ...models.match_spec import MatchSpec
from ...models.prefix_graph import PrefixGraph
from ...models.version import VersionOrder
from .classic import Solver, get_pinned_specs


log = getLogger(__name__)


class LibMambaSolver(Solver):
    """
    This alternative Solver logic wraps ``libmamba`` through their Python bindings.

    We mainly replace ``Solver.solve_final_state``, quite high in the abstraction
    tree, which means that ``conda.resolve`` and ``conda.common.logic`` are no longer
    used here. All those bits are replaced by the logic implemented in ``libmamba`` itself.

    This means that ``libmamba`` governs processes like:

    - Building the SAT clauses
    - Pruning the repodata (?) - JRG: Not sure if this happens internally or at all.
    - Prioritizing different aspects of the solver (version, build strings, track_features...)
    """
    _uses_ssc = False

    def solve_final_state(self, update_modifier=NULL, deps_modifier=NULL, prune=NULL,
                          ignore_pinned=NULL, force_remove=NULL, force_reinstall=NULL,
                          should_retry_solve=False):
        # Logic heavily based on Mamba's implementation (solver parts):
        # https://github.com/mamba-org/mamba/blob/fe4ecc5061a49c5b400fa7e7390b679e983e8456/mamba/mamba.py#L289

        if not context.json and not context.quiet:
            print("------ USING EXPERIMENTAL LIBMAMBA INTEGRATIONS ------")

        # 0. Identify strategies
        kwargs = self._merge_signature_flags_with_context(
            update_modifier=update_modifier,
            deps_modifier=deps_modifier,
            prune=prune,
            ignore_pinned=ignore_pinned,
            force_remove=force_remove,
            force_reinstall=force_reinstall,
            should_retry_solve=should_retry_solve
        )

        # Tasks that do not require a solver can be tackled right away
        # This returns either None (did nothing) or a final state
        none_or_final_state = self._early_exit_tasks(
            update_modifier=kwargs["update_modifier"],
            force_remove=kwargs["force_remove"],
        )
        if none_or_final_state is not None:
            return none_or_final_state

        # These tasks DO need a solver
        # 1. Populate repos with installed packages
        state = self._setup_state()

        # This might be too many attempts in large environments
        # We are technically allowing as many conflicts as packages
        # Mamba will only report one problem at a time for now, so
        # this is a limitation
        n_installed_pkgs = len(state["installed_pkgs"])
        attempts = n_installed_pkgs
        while attempts:
            attempts -= 1
            log.debug(
                "Attempt number %s. Current conflicts (including learnt ones): %s",
                n_installed_pkgs-attempts,
                state['conflicting'],
            )
            result = self._solve_attempt(state, kwargs)
            if result is not None:
                return result

        # Last attempt, we report everything installed as a conflict just in case
        log.debug("Last attempt: reporting all installed as conflicts:")
        state["conflicting"].update(
            {pkg.name: pkg.to_match_spec() for pkg in state["conda_prefix_data"].iter_records()
             if not pkg.is_unmanageable}
        )
        result = self._solve_attempt(state, kwargs)
        if result is not None:
            return result

        # If we didn't return already, raise last known issue.
        problems = state["solver"].problems_to_str()
        log.debug("We didn't find a solution. Reporting problems: %s", problems)
        raise self.raise_for_problems(problems)

    def _solve_attempt(self, state, kwargs):
        # 2. Create solver and needed flags, tasks and jobs
        self._configure_solver(
            state,
            update_modifier=kwargs["update_modifier"],
            deps_modifier=kwargs["deps_modifier"],
            ignore_pinned=kwargs["ignore_pinned"],
            force_remove=kwargs["force_remove"],
            force_reinstall=kwargs["force_reinstall"],
            prune=kwargs["prune"],
        )
        # 3. Run the SAT solver
        success = self._run_solver(state)
        if not success:
            # conflicts were reported, try again
            # an exception will be raised from _run_solver
            # if we end up in a conflict loop
            log.debug("Failed attempt!")
            return
        # 4. Export back to conda
        self._export_final_state(state)
        # 5. Refine solutions depending on the value of some modifier flags
        return self._post_solve_tasks(
            state,
            update_modifier=kwargs["update_modifier"],
            deps_modifier=kwargs["deps_modifier"],
            ignore_pinned=kwargs["ignore_pinned"],
            force_remove=kwargs["force_remove"],
            force_reinstall=kwargs["force_reinstall"],
            prune=kwargs["prune"],
        )

    def _merge_signature_flags_with_context(
            self,
            update_modifier=NULL,
            deps_modifier=NULL,
            ignore_pinned=NULL,
            force_remove=NULL,
            force_reinstall=NULL,
            prune=NULL,
            should_retry_solve=False):
        """
        Context options can be overriden with the signature flags.

        We need this, at least, for some unit tests that change this behaviour through
        the function signature instead of the context / env vars.
        """
        # Sometimes a str is passed instead of the Enum item
        str_to_enum = {
            "NOT_SET": DepsModifier.NOT_SET,
            "NO_DEPS": DepsModifier.NO_DEPS,
            "ONLY_DEPS": DepsModifier.ONLY_DEPS,
            "SPECS_SATISFIED_SKIP_SOLVE": UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE,
            "FREEZE_INSTALLED": UpdateModifier.FREEZE_INSTALLED,
            "UPDATE_DEPS": UpdateModifier.UPDATE_DEPS,
            "UPDATE_SPECS": UpdateModifier.UPDATE_SPECS,
            "UPDATE_ALL": UpdateModifier.UPDATE_ALL,
        }

        def context_if_null(name, value):
            return getattr(context, name) if value is NULL else str_to_enum.get(value, value)

        return {
            "update_modifier": context_if_null("update_modifier", update_modifier),
            "deps_modifier": context_if_null("deps_modifier", deps_modifier),
            "ignore_pinned": context_if_null("ignore_pinned", ignore_pinned),
            "force_remove": context_if_null("force_remove", force_remove),
            "force_reinstall": context_if_null("force_reinstall", force_reinstall),
            "prune": prune,
            # We don't use these flags in mamba
            # "should_retry_solve": should_retry_solve,
        }

    def _early_exit_tasks(self, update_modifier=NULL, force_remove=NULL):
        """
        This reimplements a chunk of code found in the Classic implementation.

        See https://github.com/conda/conda/blob/9e9461760bbd71a17822/conda/core/solve.py#L239-L256
        """
        # force_remove is a special case where we return early
        if self.specs_to_remove and force_remove:
            if self.specs_to_add:
                # This is not reachable from the CLI, but it is from the Python API
                raise NotImplementedError("Cannot add and remove packages simultaneously.")
            pkg_records = PrefixData(self.prefix).iter_records()
            solution = tuple(pkg_record for pkg_record in pkg_records
                             if not any(spec.match(pkg_record) for spec in self.specs_to_remove))
            return IndexedSet(PrefixGraph(solution).graph)

        # Check if specs are satisfied by current environment. If they are, exit early.
        if (update_modifier == UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE
                and not self.specs_to_remove):
            prefix_data = PrefixData(self.prefix)
            for spec in self.specs_to_add:
                if not next(prefix_data.query(spec), None):
                    break
            else:
                # All specs match a package in the current environment.
                # Return early, with a solution that should just be PrefixData().iter_records()
                return IndexedSet(PrefixGraph(prefix_data.iter_records()).graph)

    def _setup_state(self):
        import libmambapy as api
        from .libmamba_utils import load_channels, get_installed_jsonfile, init_api_context

        init_api_context()

        pool = api.Pool()
        state = {}

        # TODO: Check if this update-related logic is needed here too
        # Maybe conda already handles that beforehand
        # https://github.com/mamba-org/mamba/blob/fe4ecc5061a49c5b400fa7/mamba/mamba.py#L426-L485

        # https://github.com/mamba-org/mamba/blob/89174c0dc06398c99589/src/core/prefix_data.cpp#L13
        # for the C++ implementation of PrefixData
        mamba_prefix_data = api.PrefixData(self.prefix)
        mamba_prefix_data.load()
        installed_json_f, installed_pkgs = get_installed_jsonfile(self.prefix)
        repos = []
        installed = api.Repo(pool, "installed", installed_json_f.name, "")
        installed.set_installed()
        repos.append(installed)

        # This function will populate the pool/repos with
        # the current state of the given channels
        # Note load_channels has a `repodata_fn` arg we are NOT using
        # because `current_repodata.json` is not guaranteed to exist in
        # our current implementation; we bypass that and always use the
        # default value: repodata.json
        subdirs = self.subdirs
        if subdirs is NULL or not subdirs:
            subdirs = context.subdirs
        index = load_channels(pool, self._channel_urls(), repos,
                              prepend=False,
                              use_local=context.use_local,
                              platform=subdirs)

        state.update({
            "pool": pool,
            "mamba_prefix_data": mamba_prefix_data,
            "conda_prefix_data": PrefixData(self.prefix),
            "repos": repos,
            "index": index,
            "installed_pkgs": installed_pkgs,
            "history": History(self.prefix),
            "conflicting": TrackedDict(),
            "specs_map": TrackedDict(),
        })

        return state

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

    def _configure_solver(self,
                          state,
                          update_modifier=NULL,
                          deps_modifier=NULL,
                          ignore_pinned=NULL,
                          force_remove=NULL,
                          force_reinstall=NULL,
                          prune=NULL):
        if self.specs_to_remove:
            return self._configure_solver_for_remove(state)
        # ALl other operations are handled as an install operation
        # Namely:
        # - Explicit specs added by user in CLI / API
        # - conda update --all
        # - conda create -n empty
        # Take into account that early exit tasks (force remove, etc)
        # have been handled beforehand if needed
        return self._configure_solver_for_install(state,
                                                  update_modifier=update_modifier,
                                                  deps_modifier=deps_modifier,
                                                  ignore_pinned=ignore_pinned,
                                                  force_remove=force_remove,
                                                  force_reinstall=force_reinstall,
                                                  prune=prune)

    def _configure_solver_for_install(self,
                                      state,
                                      update_modifier=NULL,
                                      deps_modifier=NULL,
                                      ignore_pinned=NULL,
                                      force_remove=NULL,
                                      force_reinstall=NULL,
                                      prune=NULL):
        import libmambapy as api

        # Set different solver options
        solver_options = [(api.SOLVER_FLAG_ALLOW_DOWNGRADE, 1)]
        if context.channel_priority is ChannelPriority.STRICT:
            solver_options.append((api.SOLVER_FLAG_STRICT_REPO_PRIORITY, 1))
        state["solver"] = solver = api.Solver(state["pool"], solver_options)

        # Configure jobs
        state["specs_map"] = self._compute_specs_map(state,
                                                     update_modifier=update_modifier,
                                                     deps_modifier=deps_modifier,
                                                     ignore_pinned=ignore_pinned,
                                                     force_remove=force_remove,
                                                     force_reinstall=force_reinstall,
                                                     prune=prune)

        # Neuter conflicts if any (modifies specs_map in place)
        specs_map = self._neuter_conflicts(state, ignore_pinned=ignore_pinned)

        tasks = self._specs_map_to_tasks(state, specs_map)

        log.debug(
            "Invoking libmamba with tasks: %s",
            "\n".join([f"{task_str}: {', '.join(specs)}"
                       for (task_str, _), specs in tasks.items()])
        )

        for (_, task_type), specs in tasks.items():
            solver.add_jobs(sorted(specs), task_type)

        return solver

    def _configure_solver_for_remove(self, state):
        # First check we are not trying to remove things that are not installed
        installed_names = set(rec.name for rec in state["conda_prefix_data"].iter_records())
        not_installed = set(s for s in self.specs_to_remove if s.name not in installed_names)
        if not_installed:
            raise PackagesNotFoundError(not_installed)

        import libmambapy as api

        solver_options = [
            (api.SOLVER_FLAG_ALLOW_DOWNGRADE, 1),
            (api.SOLVER_FLAG_ALLOW_UNINSTALL, 1)
        ]
        if context.channel_priority is ChannelPriority.STRICT:
            solver_options.append((api.SOLVER_FLAG_STRICT_REPO_PRIORITY, 1))
        solver = api.Solver(state["pool"], solver_options)

        # pkgs in aggresive_update_packages should be protected too (even if not
        # requested explicitly by the user)
        # see https://github.com/conda/conda/blob/9e9461760bb/tests/core/test_solve.py#L520-L521
        aggresive_updates = [p.conda_build_form() for p in context.aggressive_update_packages
                             if p.name in installed_names]
        solver.add_jobs(
            list(set(chain(self._history_specs(), aggresive_updates))),
            api.SOLVER_USERINSTALLED,
        )
        specs = [s.conda_build_form() for s in self.specs_to_remove]
        solver.add_jobs(specs, api.SOLVER_ERASE | api.SOLVER_CLEANDEPS)

        state["solver"] = solver
        return solver

    def _compute_specs_map(self,
                           state,
                           update_modifier=NULL,
                           deps_modifier=NULL,
                           ignore_pinned=NULL,
                           force_remove=NULL,
                           force_reinstall=NULL,
                           prune=NULL):
        """
        Reimplement the logic found in super()._collect_all_metadata()
        and super()._add_specs(), but simplified.
        """
        # Section 1: Expose the prefix state

        # This will be our `ssc.specs_map`; a dict of names->MatchSpec that
        # will contain the specs passed to the solver (eventually). Mamba
        # expects a MatchSpec.conda_build_form(), but internally we will use
        # the full object to handle things like optionality and targets.
        specs_map = TrackedDict()
        history = state["history"].get_requested_specs_map()
        installed = {p.name: p for p in state["conda_prefix_data"].iter_records()}
        pinned = {p.name: p for p in self._pinned_specs(state, ignore_pinned)}
        conflicting = state["conflicting"]

        # 1.1. Add everything found in history
        log.debug("Adding history pins")
        specs_map.update(history)
        # 1.2. Protect some critical packages from being removed accidentally
        for pkg_name in ('anaconda', 'conda', 'conda-build', 'python.app',
                         'console_shortcut', 'powershell_shortcut'):
            if pkg_name not in specs_map and state["conda_prefix_data"].get(pkg_name, None):
                specs_map[pkg_name] = MatchSpec(pkg_name)

        # 1.3. Add virtual packages so they are taken into account by the solver
        log.debug("Adding virtual packages")
        virtual_pkg_index = {}
        _supplement_index_with_system(virtual_pkg_index)
        for virtual_pkg in virtual_pkg_index.keys():
            if virtual_pkg.name not in specs_map:
                specs_map[virtual_pkg.name] = MatchSpec(virtual_pkg.name)

        # 1.4. Go through the installed packages and...
        log.debug("Relaxing some installed specs")
        for pkg_name, pkg_record in installed.items():
            name_spec = MatchSpec(pkg_name)
            if (  # 1.4.1. History is empty. Add everything (happens with update --all)
                    not history
                  # 1.4.2. Pkg is part of the aggresive update list
                    or name_spec in context.aggressive_update_packages
                  # 1.4.3. it was installed with pip/others; treat it as a historic package
                    or pkg_record.subdir == 'pypi'):
                specs_map[pkg_name] = name_spec

        # Section 2 - Here we technically consider the packages that need to be removed
        # but we are handling that as a separate action right now - TODO?

        # Section 3 - Refine specs implicitly by the prefix state
        #
        # 3.1. If the prefix already contain matching specs for what we have added so far,
        # constrain these whenever possible to reduce the amount of changes
        log.debug("Refining some installed packages...")
        for pkg_name, pkg_spec in specs_map.items():
            matches_for_spec = tuple(prec for prec in installed.values() if pkg_spec.match(prec))
            if not matches_for_spec:
                continue
            if len(matches_for_spec) > 1:
                raise CondaError(
                    "Your prefix contains more than one possible match for the requested spec!\n"
                    f"  pkg_name: {pkg_name}\n"
                    f"  spec: {pkg_spec}\n"
                    f"  matches_for_spec: {matches_for_spec}\n"
                )
            spec_in_prefix = matches_for_spec[0]
            # 3.1.1: always update
            if MatchSpec(pkg_name) in context.aggressive_update_packages:
                log.debug("Relax due to aggressive_update_packages")
                specs_map[pkg_name] = MatchSpec(pkg_name)
            # 3.1.2: freeze
            elif spec_in_prefix.is_unmanageable:
                log.debug("Freeze because unmanageable")
                # TODO: This is not the complete _should_freeze logic
                specs_map[pkg_name] = spec_in_prefix.to_match_spec()
            elif not history:
                log.debug("Freeze because no history")
                # TODO: This is not the complete _should_freeze logic
                specs_map[pkg_name] = spec_in_prefix.to_match_spec()
            elif pkg_name not in conflicting:
                log.debug("Freeze because not conflicting")
                # TODO: This is not the complete _should_freeze logic
                specs_map[pkg_name] = spec_in_prefix.to_match_spec()
            # 3.1.3: soft-constrain via `target`
            elif pkg_name in history:
                log.debug("Soft-freezing because historic")
                specs_map[pkg_name] = MatchSpec(
                    history[pkg_name], target=spec_in_prefix.dist_str())
            else:
                log.debug("Soft-freezing because it is requested and "
                          "already installed as a 2nd order dependency")
                specs_map[pkg_name] = MatchSpec(pkg_name, target=spec_in_prefix.dist_str())

        # Section 4: Check pinned packages
        from mamba.repoquery import depends as mamba_depends

        pin_overrides = set()
        explicit_pool = set()
        for spec in self.specs_to_add:
            result = mamba_depends(spec.dist_str(), pool=state["pool"])
            explicit_pool.update([p["name"] for p in result["result"]["pkgs"]])

        specs_to_add_map = {s.name: s for s in self.specs_to_add}
        for name, pin in pinned.items():
            is_installed = name in installed
            is_requested = name in specs_to_add_map
            if is_installed and not is_requested:
                log.debug("Pinning because installed and not requested")
                specs_map[name] = MatchSpec(pin, optional=False)
            elif is_requested:
                log.debug("Pin overrides user-requested spec")
                if specs_to_add_map[name].match(pin):
                    log.debug("pinned spec `%s` despite user-requested spec `%s` being present "
                              "because pin is stricter", pin, specs_to_add_map[name])
                    specs_map[name] = MatchSpec(pin, optional=False)
                    pin_overrides.add(name)
                else:
                    log.warn("pinned spec %s conflicts with explicit specs (%s).  "
                             "Overriding pinned spec.", pin, specs_to_add_map[name])
            elif name in explicit_pool:
                log.debug("Pinning because this spec is part of the explicit pool")
                specs_map[name] = MatchSpec(pin, optional=False)
            # TODO: Not sure what this does
            # elif installed[pin.name] & r._get_package_pool([pin]).get(pin.name, set()):
            #     specs_map[pin.name] = MatchSpec(pin, optional=False)
            #     pin_overrides.add(pin.name)

        # Section 5: freeze everything that is not currently in conflict
        if update_modifier == UpdateModifier.FREEZE_INSTALLED:
            for pkg_name, pkg_record in installed.items():
                if pkg_name not in conflicting:  # TODO
                    log.debug("Freezing because installed and not conflicting")
                    specs_map[pkg_name] = pkg_record.to_match_spec()
                elif not pkg_record.is_unmanageable:
                    log.debug("Unfreezing because conflicting...")
                    specs_map[pkg_name] = MatchSpec(
                        pkg_name, target=pkg_record.to_match_spec(), optional=True)
            # log.debug("specs_map with targets: %s", specs_map)

        # Section 6: Handle UPDATE_ALL
        elif update_modifier == UpdateModifier.UPDATE_ALL:
            new_specs_map = TrackedDict()
            if history:
                for spec in history:
                    matchspec = MatchSpec(spec)
                    if matchspec.name not in pinned:
                        log.debug("Update all: spec is in history but not pinnned")
                        new_specs_map[spec] = matchspec
                    else:
                        log.debug("Update all: spec is in history and pinnned")
                        new_specs_map[matchspec.name] = specs_map[matchspec.name]
                for pkg_name, pkg_record in installed.items():
                    # treat pip-installed stuff as explicitly installed, too.
                    if pkg_record.subdir == 'pypi':
                        log.debug("Update all: spec is pip-installed")
                        new_specs_map[pkg_name] = MatchSpec(pkg_name)
                    elif pkg_name not in new_specs_map:
                        log.debug("Update all: adding spec to list because it was installed")
                        new_specs_map[pkg_name] = MatchSpec(pkg_name)
            else:
                for pkg_name, pkg_record in installed.items():
                    if pkg_name not in pinned:
                        log.debug("Update all: spec is installed but not pinned")
                        new_specs_map[pkg_name] = MatchSpec(pkg_name)
                    else:
                        log.debug("Update all: spec is installed and pinned")
                        new_specs_map[pkg_name] = specs_map[pkg_name]
            # We overwrite the specs map so far!
            specs_map = new_specs_map

        # Section 6 - Handle UPDATE_SPECS (note: this might be unimportant)
        # Unfreezes the indirect specs that otherwise conflict
        # with the update of the explicitly requested spec
        elif update_modifier == UpdateModifier.UPDATE_SPECS:
            from mamba.repoquery import search as mamba_search
            potential_conflicts = []
            for spec in self.specs_to_add:  # requested by the user
                in_pins = spec.name not in pin_overrides and spec.name in pinned
                in_history = spec.name in history
                if in_pins or in_history:  # skip these
                    continue
                has_update = False
                # Check if this spec has any available updates
                installed_record = installed.get(spec.name)

                if installed_record:
                    # Check the index for available updates
                    installed_version = VersionOrder(installed_record.version)
                    query = mamba_search(f"{spec.name} >={installed_version}", pool=state["pool"])
                    for pkg_record in query["result"]["pkgs"]:
                        if pkg_record["channel"] == "installed":
                            continue
                        found_version = VersionOrder(pkg_record["version"])
                        greater_version = found_version > installed_version
                        greater_build = (
                            found_version == installed_version and
                            pkg_record["build_number"] > installed_record.build_number
                        )
                        if greater_version or greater_build:
                            has_update = True
                            break
                if has_update:
                    potential_conflicts.append(
                        MatchSpec(
                            spec.name,
                            version=pkg_record["version"],
                            build_number=pkg_record["build_number"],
                        )
                    )
                else:
                    potential_conflicts.append(spec)

            # TODO: What shall we do with `potential_conflicts`??

            log.debug("Relax constrains because it caused a conflict")
            for pkg in conflicting.values():
                # neuter the spec due to a conflict
                if pkg.name in specs_map and pkg.name not in pinned:
                    specs_map[pkg.name] = history.get(pkg.name, MatchSpec(pkg.name))

        # Section 7 - Pin Python
        log.debug("Adjust python pinning")
        py_requested_explicitly = any(s.name == "python" for s in self.specs_to_add)
        installed_python = installed.get("python")
        if installed_python and not py_requested_explicitly:
            freeze_installed = update_modifier == UpdateModifier.FREEZE_INSTALLED
            if "python" not in conflicting and freeze_installed:
                specs_map["python"] = installed_python.to_match_spec()
            else:
                # will our prefix record conflict with any explict spec?  If so, don't add
                #     anything here - let python float when it hasn't been explicitly specified
                python_spec = specs_map.get("python", MatchSpec("python"))
                if not python_spec.get('version'):
                    pinned_version = get_major_minor_version(installed_python.version) + '.*'
                    python_spec = MatchSpec(python_spec, version=pinned_version)
                specs_map["python"] = python_spec

        # Section 8 - Make sure aggressive updates are not constrained now
        if not context.offline:
            log.debug("Make sure aggressive updates did not end up pinned again")
            specs_map.update({s.name: s for s in context.aggressive_update_packages
                              if s.name in specs_map})

        # Section 9 - FINALLY we add the explicitly requested specs
        log.debug("Add user specs")
        specs_map.update({s.name: s for s in self.specs_to_add if s.name not in pin_overrides})

        # Section 10 - Make sure `conda` is not downgraded
        if "conda" in specs_map and paths_equal(self.prefix, context.conda_prefix):
            conda_prefix_rec = state["conda_prefix_data"].get("conda")
            if conda_prefix_rec:
                version_req = f">={conda_prefix_rec.version}"
                conda_requested_explicitly = any(s.name == "conda" for s in self.specs_to_add)
                conda_spec = specs_map["conda"]
                conda_in_specs_to_add_version = specs_map.get("conda", {}).get("version")
                if not conda_in_specs_to_add_version:
                    conda_spec = MatchSpec(conda_spec, version=version_req)
                if context.auto_update_conda and not conda_requested_explicitly:
                    conda_spec = MatchSpec("conda", version=version_req, target=None)
                log.debug("Adjust conda spec")
                specs_map["conda"] = conda_spec

        # Section 11 - Mamba/Conda behaviour difference workaround
        # If a spec is installed and has been requested with no constrains,
        # we assume the user wants an update, so we add >{current_version}, but only if no
        # flags have been passed -- otherwise interactions between implicit updates create unneeded
        # conflicts
        log.debug("Make sure specs are upgraded if requested explicitly and not in conflict")
        if (deps_modifier != DepsModifier.ONLY_DEPS
                and update_modifier not in
                (UpdateModifier.UPDATE_DEPS, UpdateModifier.FREEZE_INSTALLED)
                and self._command in ("update", "", None, NULL)):
            for spec in self.specs_to_add:
                if (spec.name in specs_map and specs_map[spec.name].strictness == 1
                        and spec.name in installed):
                    conflicting_spec = conflicting.get(spec.name)
                    if conflicting_spec and getattr(conflicting_spec, "missing", False):
                        # We obtained a "nothing provides" error, which means this
                        # spec cannot be updated further; no forced update then
                        # TODO: Refactor conflict into dict of dicts with name->spec,reason
                        continue
                    if spec.name in ("pip", "setuptools"):
                        # If added with no constrains, excluding their installed version can
                        # result in unneded python downgrades
                        # see tests/conda_env/test_cli.py::test_update_env_no_action_json_output
                        continue
                    installed_version = installed[spec.name].version
                    if installed_version:
                        # TODO: We might want to say "any version or build of this package",
                        # but not the installed one
                        specs_map[spec.name] = MatchSpec(
                            name=spec.name,
                            version=f"!={installed_version}")

        return specs_map

    def _neuter_conflicts(self, state, ignore_pinned=False):
        conflicting_specs = state["conflicting"].values()
        specs_map = state["specs_map"]

        # Are all conflicting specs in specs_map? If not, that means they're in
        # track_features_specs or pinned_specs, which we should raise an error on.
        # JRG: This won't probably work because Mamba reports conflicts one at a time...
        specs_set = set(specs_map.values())
        grouped_specs = groupby(lambda s: s in specs_set, conflicting_specs)
        # force optional to true. This is what it is originally in
        # pinned_specs, but we override that in _compute_specs_map to make it
        # non-optional when there's a name match in the explicit package pool
        conflicting_pinned_specs = groupby(
            lambda s: MatchSpec(s, optional=True) in self._pinned_specs(state, ignore_pinned),
            conflicting_specs)

        if conflicting_pinned_specs.get(True):
            in_specs_map = grouped_specs.get(True, ())
            pinned_conflicts = conflicting_pinned_specs.get(True, ())
            in_specs_map_or_specs_to_add = ((set(in_specs_map) | set(self.specs_to_add))
                                            - set(pinned_conflicts))

            raise SpecsConfigurationConflictError(
                sorted(s.__str__() for s in in_specs_map_or_specs_to_add),
                sorted(s.__str__() for s in {s for s in pinned_conflicts}),
                self.prefix
            )

        log.debug("Neutering specs...")
        for spec in conflicting_specs:
            # if spec.name == "python":
            #     continue
            if spec.target and not spec.optional:
                if spec.get('version'):
                    neutered_spec = MatchSpec(spec.name, version=spec.version)
                else:
                    neutered_spec = MatchSpec(spec.name)
                specs_map[spec.name] = neutered_spec
            if spec.name not in specs_map:
                # side-effect conflict; add to specs with less restrains
                specs_map[spec.name] = MatchSpec(name=spec.name, target=spec.dist_str())

        return specs_map

    def _specs_map_to_tasks(self, state, specs_map):
        import libmambapy as api

        tasks = defaultdict(list)
        history = state["history"].get_requested_specs_map()
        specs_map = specs_map.copy()
        installed = {rec.name: rec for rec in state["conda_prefix_data"].iter_records()}

        # Section 11 - deprioritize installed stuff that wasn't requested
        # These packages might not be available in future Python versions, but we don't
        # want them to block a requested Python update
        log.debug("Deprioritizing conflicts:")
        protect_these = set(s.name for s in self.specs_to_add)  # explicitly requested
        protect_these.update(("python", "conda"))
        protect_these.update([pkg_name for pkg_name, pkg_record in installed.items()
                              if pkg_record.is_unmanageable])
        for conflict in state["conflicting"]:
            if conflict in specs_map and conflict not in protect_these:
                spec = specs_map.pop(conflict)
                log.debug("  MOV: %s from specs_map to SOLVER_DISFAVOR", conflict)
                tasks[("api.SOLVER_DISFAVOR", api.SOLVER_DISFAVOR)].append(
                    spec.conda_build_form())
                tasks[("api.SOLVER_ALLOWUNINSTALL", api.SOLVER_ALLOWUNINSTALL)].append(
                    spec.conda_build_form())

        # Wrap up and create tasks for the solver
        for name, spec in specs_map.items():
            if name.startswith("__"):
                continue
            if name in installed:
                if name == "python":
                    key = ("api.SOLVER_UPDATE | api.SOLVER_ESSENTIAL",
                           api.SOLVER_UPDATE | api.SOLVER_ESSENTIAL)
                else:
                    key = "api.SOLVER_UPDATE", api.SOLVER_UPDATE

                history_spec = history.get(name)
                if history_spec:
                    installed_rec = installed[name]
                    ms = MatchSpec(
                        name=installed_rec.name,
                        version=installed_rec.version,
                        build=installed_rec.build)
                    tasks[("api.SOLVER_USERINSTALLED", api.SOLVER_USERINSTALLED)].append(
                        ms.conda_build_form())
            else:
                key = "api.SOLVER_INSTALL", api.SOLVER_INSTALL
            tasks[key].append(spec.conda_build_form())

        return tasks

    def _pinned_specs(self, state, ignore_pinned=False):
        if ignore_pinned:
            return ()
        pinned_specs = get_pinned_specs(self.prefix)
        pin_these_specs = []
        for pin in pinned_specs:
            installed_pins = state["conda_prefix_data"].query(pin.name) or ()
            for installed in installed_pins:
                if not pin.match(installed):
                    raise SpecsConfigurationConflictError([installed], [pin], self.prefix)
            pin_these_specs.append(pin)
        return tuple(pin_these_specs)

    def _history_specs(self):
        return [s.conda_build_form()
                for s in History(self.prefix).get_requested_specs_map().values()]

    def _run_solver(self, state):
        solver = state["solver"]
        solved = solver.solve()
        if solved:
            # Clear potential conflicts we used to have
            state["conflicting"].clear()
        else:
            # Report problems if any
            # it would be better if we could pass a graph object or something
            # that the exception can actually format if needed
            problems = solver.problems_to_str()
            state["conflicting"] = self._parse_problems(problems, state["conflicting"].copy())
            log.debug("Attempt failed with %s", problems)

        return solved

    def _export_final_state(self, state):
        import libmambapy as api
        from .libmamba_utils import to_package_record_from_subjson

        solver = state["solver"]
        index = state["index"]
        installed_pkgs = state["installed_pkgs"]

        transaction = api.Transaction(
            solver,
            api.MultiPackageCache(context.pkgs_dirs),
        )
        (names_to_add, names_to_remove), to_link, to_unlink = transaction.to_conda()

        # What follows below is taken from mamba.utils.to_txn with some patches
        conda_prefix_data = PrefixData(self.prefix)
        final_precs = IndexedSet(conda_prefix_data.iter_records())

        lookup_dict = {}
        for _, entry in index:
            lookup_dict[
                entry["channel"].platform_url(entry["platform"], with_credentials=False)
            ] = entry

        for _, pkg in to_unlink:
            for i_rec in installed_pkgs:
                # Do not try to unlink virtual pkgs, virtual eggs, etc
                if not i_rec.is_unmanageable and i_rec.fn == pkg:
                    final_precs.remove(i_rec)
                    break
            else:
                log.warn("Tried to unlink %s but it is not installed or manageable?", pkg)

        for c, pkg, jsn_s in to_link:
            if c.startswith("file://"):
                # The conda functions (specifically remove_auth) assume the input
                # is a url; a file uri on windows with a drive letter messes them up.
                key = c
            else:
                key = split_anaconda_token(remove_auth(c))[0]
            if key not in lookup_dict:
                raise ValueError("missing key {} in channels: {}".format(key, lookup_dict))
            sdir = lookup_dict[key]
            rec = to_package_record_from_subjson(sdir, pkg, jsn_s)
            final_precs.add(rec)

        # state["old_specs_to_add"] = self.specs_to_add
        # state["old_specs_to_remove"] = self.specs_to_remove
        state["final_prefix_state"] = final_precs
        state["names_to_add"] = [name for name in names_to_add if not name.startswith("__")]
        state["names_to_remove"] = [name for name in names_to_remove if not name.startswith("__")]

        return state

    def _parse_problems(self, problems, previous):
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
            conflicts[name].missing = conflict in missing
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
            self.raise_for_problems(problems)

        # Preserve old conflicts (now neutered as name-only spes) in the
        # new list of conflicts (unless a different variant is now present)
        # This allows us to have a conflict memory for next attempts.
        for name, spec in previous.items():
            if name not in conflicts:
                conflicts[name] = spec
        return conflicts

    def _post_solve_tasks(self,
                          state,
                          deps_modifier=NULL,
                          update_modifier=NULL,
                          force_reinstall=NULL,
                          ignore_pinned=NULL,
                          force_remove=NULL,
                          prune=NULL):
        specs_map = state["specs_map"]
        final_prefix_map = TrackedDict({pkg.name: pkg for pkg in state["final_prefix_state"]})
        history_map = state["history"].get_requested_specs_map()
        self.neutered_specs = tuple(pkg_spec for pkg_name, pkg_spec in specs_map.items() if
                                    pkg_name in history_map and
                                    pkg_spec.strictness < history_map[pkg_name].strictness)

        # TODO: We are currently not handling dependencies orphaned after identifying
        # conflicts (stored in `ssc.add_back_map`).

        if deps_modifier == DepsModifier.NO_DEPS:
            # In the NO_DEPS case, we need to start with the original list of packages in the
            # environment, and then only modify packages that match specs_to_add or
            # specs_to_remove.
            #
            # Help information notes that use of NO_DEPS is expected to lead to broken
            # environments.
            _no_deps_solution = IndexedSet(state["conda_prefix_data"].iter_records())
            only_remove_these = set(prec
                                    for name in state["names_to_remove"]
                                    for prec in _no_deps_solution
                                    if MatchSpec(name).match(prec))
            _no_deps_solution -= only_remove_these

            only_add_these = set(prec
                                 for name in state["names_to_add"]
                                 for prec in state["final_prefix_state"]
                                 if MatchSpec(name).match(prec))
            remove_before_adding_back = set(prec.name for prec in only_add_these)
            _no_deps_solution = IndexedSet(prec for prec in _no_deps_solution
                                           if prec.name not in remove_before_adding_back)
            _no_deps_solution |= only_add_these
            final_prefix_map = {p.name: p for p in _no_deps_solution}

        # If ONLY_DEPS is set, we need to make sure the originally requested specs
        # are not part of the result
        elif (deps_modifier == DepsModifier.ONLY_DEPS
              and update_modifier != UpdateModifier.UPDATE_DEPS):
            graph = PrefixGraph(state["final_prefix_state"], self.specs_to_add)
            removed_nodes = graph.remove_youngest_descendant_nodes_with_specs()
            specs_to_add = set(MatchSpec(name) for name in state["names_to_add"])
            for pkg_record in removed_nodes:
                for dependency in pkg_record.depends:
                    dependency = MatchSpec(dependency)
                    if dependency.name not in specs_map:
                        specs_to_add.add(dependency)
            state["names_to_add"] = set(spec.name for spec in specs_to_add)

            # Add back packages that are already in the prefix.
            specs_to_remove_names = set(name for name in state["names_to_remove"])
            add_back = [state["conda_prefix_data"].get(node.name, None) for node in removed_nodes
                        if node.name not in specs_to_remove_names]
            final_prefix_map = {p.name: p for p in concatv(graph.graph, filter(None, add_back))}

        elif update_modifier == UpdateModifier.UPDATE_DEPS:
            # This code below is adapted from the classic solver logic
            # found in Solver._post_sat_handling()

            # We need a post-solve to find the full chain of dependencies
            # for the requested specs (1) The previous solve gave us
            # the packages that would be installed normally. We take
            # that list and process their dependencies too so we can add
            # those explicitly to the list of packages to be updated.
            # If additionally DEPS_ONLY is set, we need to remove the
            # originally requested specs from the final list of explicit
            # packages.

            # (2) Get the dependency tree for each dependency
            graph = PrefixGraph(state["final_prefix_state"])
            update_names = set()
            for spec in self.specs_to_add:
                node = graph.get_node_by_name(spec.name)
                update_names.update(ancest_rec.name for ancest_rec in graph.all_ancestors(node))
            specs_map = TrackedDict({name: MatchSpec(name) for name in update_names})

            # Remove pinned_specs and any python spec (due to major-minor pinning business rule).
            for spec in self._pinned_specs(state, ignore_pinned):
                specs_map.pop(spec.name, None)
            # TODO: This kind of version constrain patching is done several times in different
            # parts of the code, so it might be a good candidate for a dedicate utility function
            if "python" in specs_map:
                python_rec = state["conda_prefix_data"].get("python")
                py_ver = ".".join(python_rec.version.split(".")[:2]) + ".*"
                specs_map["python"] = MatchSpec(name="python", version=py_ver)

            # Add in the original specs_to_add on top.
            specs_map.update({spec.name: spec for spec in self.specs_to_add})

            with context.override("quiet", True):
                # Create a new solver instance to perform a 2nd solve with deps added
                # We do it like this to avoid overwriting state accidentally. Instead,
                # we will import the needed state bits manually.
                solver2 = self.__class__(self.prefix, self.channels, self.subdirs,
                                         list(specs_map.values()), self.specs_to_remove,
                                         self._repodata_fn, "recursive_call_for_update_deps")
                solved_pkgs = solver2.solve_final_state(
                    update_modifier=UpdateModifier.UPDATE_SPECS,  # avoid recursion!
                    deps_modifier=deps_modifier,
                    ignore_pinned=ignore_pinned,
                    force_remove=force_remove,
                    force_reinstall=force_reinstall,
                    prune=prune)
                final_prefix_map = {p.name: p for p in solved_pkgs}
                # NOTE: We are exporting state back to the class! These are expected by
                # super().solve_for_diff() and super().solve_for_transaction() :/
                self.specs_to_add = solver2.specs_to_add.copy()
                self.specs_to_remove = solver2.specs_to_remove.copy()

            prune = False

        # Prune leftovers
        if prune:
            graph = PrefixGraph(final_prefix_map.values(), specs_map.values())
            graph.prune()
            final_prefix_map = {p.name: p for p in graph.graph}

        # Wrap up and return the final state

        # NOTE: We are exporting state back to the class! These are expected by
        # super().solve_for_diff() and super().solve_for_transaction() :/
        # self.specs_to_add = {MatchSpec(name) for name in state["names_to_add"]
        #                      if not name.startswith("__")}
        # self.specs_to_remove = {MatchSpec(name) for name in state["names_to_remove"]
        #                         if not name.startswith("__")}

        # if on_win:
        #     # TODO: We are manually decoding local paths in windows because the colon
        #     # in paths like file:///C:/Users... gets html escaped as %3a in our workarounds
        #     # There must be a better way to do this but we will find it while cleaning up
        #     final_prefix_values = []
        #     for pkg in final_prefix_map.values():
        #         if pkg.url and pkg.url.startswith("file://") and "%" in pkg.url:
        #             pkg.url = percent_decode(pkg.url)
        #         final_prefix_values.append(pkg)
        # else:
        final_prefix_values = final_prefix_map.values()

        # TODO: Review performance here just in case
        return IndexedSet(PrefixGraph(final_prefix_values).graph)

    def raise_for_problems(self, problems):
        for line in problems.splitlines():
            line = line.strip()
            if line.startswith("- nothing provides requested"):
                packages = line.split()[4:]
                raise PackagesNotFoundError([" ".join(packages)])
        raise RawStrUnsatisfiableError(problems)


class TrackedDict(dict):
    def __setitem__(self, k, v) -> None:
        if k in self:
            oldv = self[k]
            if v == oldv:
                log.debug("  EQU: %s = %s", k, v)
            else:
                log.debug("  UPD: %s from %s to %s", k, self[k], v)
        else:
            log.debug("  NEW: %s = %s", k, v)
        return super().__setitem__(k, v)

    def __delitem__(self, v) -> None:
        log.debug("  DEL: %s", v)
        return super().__delitem__(v)

    def update(self, *args, **kwargs):
        old = self.copy()
        super().update(*args, **kwargs)
        for k, v in self.items():
            if k in old:
                oldv = old[k]
                if v != oldv:
                    log.debug("  UPD: %s from %s to %s", k, old[k], v)
            else:
                log.debug("  NEW: %s = %s", k, v)
