(deep_dive_solvers)=

# Deep dive: solvers

The guide {ref}`deep_dive_install` didn't go into details of the solver black box. It did mention
the high-level `Solver` API and how `conda` expects a Transaction out of it, but we never got to
learn what happens _inside_ the solver itself. We only covered these three steps:

> The details are complicated, but in essence, the solver will:
>
> 1. Express the requested packages, command line options and prefix state as `MatchSpec` objects
> 2. Query the index for the best possible match that satisfy those constrains
> 3. Return a list of `PackageRecord` objects.


How do we transform the prefix state and configurations into a list of `MatchSpec` objects? How
are those turned into a list of `PackageRecord` objects? Where are those `PackageRecord`
objects coming from? We are going to cover these aspects in detail here.

## `MatchSpec` vs `PackageRecord`

First, let's define what each object does:

* [`PackageRecord`][conda.models.records:PackageRecord] objects represent a concrete package
  tarball and its contents. They follow [specific naming conventions][conda_package_naming] and
  expose several fields. Inspect them directly in the
  [class code][conda.models.records:PackageRecord].
* [`MatchSpec`][conda.models.match_spec:MatchSpec] objects are essentially a query language to
  find `PackageRecord` objects. Internally, `conda` will translate your command line requests,
  like `numpy>=1.19`, `python=3.*` or `pytorch=1.8.*=*cuda*`, into instances of this class.
  This query language has its own syntax and rules, detailed [here][conda_package_spec]. The
  most important fields of a `MatchSpec` object are:
  * `name`: the name of the package (e.g. `pytorch`), always expected.
  * `version`: the version constrains (e.g. `1.8.*`), can be empty but if `build` is set, set it to
    `*` to avoid issues with the `.conda_build_form()` method.
  * `build`: the build string constrains (e.g. `*cuda*`), can be empty.

```{tip} Create a MatchSpec from a PackageRecord

You can create a `MatchSpec` object from a `PackageRecord` instance using the `.to_match_spec()`
method. This will create a `MatchSpec` object with its fields set to exactly match the originating
`PackageRecord`.
```

Note that there are two `PackageRecord` subclasses with extra fields, so we need to distinguish
between three types, all of them useful:
* `PackageRecord`: A record as present in the index (channel).
* `PackageCacheRecord`: A record already extracted in the cache. Contains extra fields for the
  tarball path in disk and its extracted directory.
* `PrefixRecord`: A record installed in a prefix. Same as above, plus fields for the files that
  make the package and how they were linked in the prefix. It can also host information about which
  `MatchSpec` string resulted into this record being installed.

## Remote state: the index

So the solver takes `MatchSpec` objects, query the index for the best match and returns
`PackageRecord` objects. Perfect. What's the index? It's the result of aggregating the
requested conda channels in a single entity. For more information, check
{ref}`deep_dive_install_index`.

## Local state: the prefix and context

When you do `conda install numpy`, do you think the solver will just see something like
`specs=[MatchSpec("numpy")]`? Well, not that quick. The explicit instructions given by the user
are only one part of the request we will send to the solver. Other pieces of implicit state are
taken into account to build the final request. Namely, the state of your prefix. In total,
these are the ingredients of the solver request.

1. Packages already present in your environment, if you are not _creating_ a new one. This is
   exposed through the `conda.core.prefix_data.PrefixData` class, which provides an iterator method
   via `.iter_records()`. As we saw before, this yields `conda.models.records.PrefixRecord`
   objects, a `PackageRecord` subclass for installed records.
2. Past actions you have performed in that environment; the _History_. This is a journal of all the
   `conda install|update|remove` commands you have run in the past. In other words, the _specs_
   matched by those previous actions will receive extra protections in the solver.
3. Packages included in the _aggressive updates_ list. These packages are always included in any
   requests to make sure they stay up-to-date under all circumstances.
4. Packages pinned to a specific version, either via `pinned_packages` in your `.condarc` or defined
   in a `$PREFIX/conda-meta/pinned` file.
5. In new environments, packages included in the `create_default_packages` list. These specs are
   injected in each `conda create` command, so the solver will see them as explicitly requested
   by the user.
6. And, finally, the specs the user is asking for. Sometimes this is explicit (e.g.
   `conda install numpy`) and sometimes a bit implicit (e.g. `conda update --all` is telling the
   solver to add all installed packages to the update list).

All of those sources of information produce a number a of `MatchSpec` objects which are then
combined and modified in very specific ways depending on the command-line flags and their origin
(e.g. specs coming from the pinned packages won't be modified, unless the user asks for it
explicitly). This logic is intricate will be covered in the next sections.

## The high-level logic in `conda.cli.install`

The full solver logic does not start at the `conda.core.solve.Solver` API, but before that, all the
way up in the `conda.cli.install` module. Here, some important decisions are already made:

* Whether the solver is not needed at all because:
    * The operation is an explicit package install
    * The user requested to roll back to a history checkpoint
    * We are just creating a copy of an existing environment (cloning)
* Which `repodata` source to use (see {ref}`here <index_reduction_tricks>`). It not only depends on
  depends on the current configuration (via `.condarc` or command line flags), but also on the value
  of `use_only_tar_bz2`.
* Whether the solver should start by freezing all installed packages (default for
  `conda install` and `conda remove` in existing environments).
* If the solver does not find a solution, whether we need to retry again without freezing the
  installed packages for the current `repodata` variant or if we should try with the next one.

So, roughly, the global logic there follows this pseudocode:

```python
if operation in (explicit, rollback, clone):
    transaction = handle_without_solver()
else:
    repodatas = from_config or ("current_repodata.json", "repodata.json")
    freeze_installed = (is_install or is_remove) and (env exists) and (update_modifier not in argv)
    for repodata in repodatas:
        try:
            transaction = solve_for_transaction(...)
        except:
            if repodata is last:
                raise
            elif freeze_installed:
                transaction = solve_for_transaction(freeze_installed = False)
            else:
                try with next repodata

handle_txn(transaction)
```

We have, then, two reasons to re-run the full Solver logic:

* Freezing the installed packages didn't work, so we try without freezing again.
* Using `current_repodata` did not work, so we try with full `repodata`.

These two strategies are stacked so in the end, before eventually failing, we will have tried four
things:

1. Solve with `current_repodata.json` and `freeze_installed=True`
2. Solve with `current_repodata.json` and `freeze_installed=False`
3. Solve with `repodata.json` and `freeze_installed=True`
4. Solve with `repodata.json` and `freeze_installed=False`

Interestingly, those strategies are designed to improve `conda`'s average performance, but they
should be seen as a risky bet. Those attempts can get expensive!

```{admonition} How to ask for a simpler approach
If you want to try the full thing without checking whether the optimized solves work, you can
override the default behaviour with these flags in your `conda install` commands:

* `--repodata-fn=repodata.json`: do not use `current_repodata.json`
* `--update-specs`: do not try to freeze installed
```

Then, the `Solver` class has its own internal logic, which also features some retry loops. This
will be discussed later and summarized.
## Early exit tasks

Some tasks do not involve the solver at all. Let's enumerate them:

* Explicit package installs: no index or prefix state needed.
* Cloning an environment: the index might be needed if the cache has been cleared.
* History rollback: currently broken.
* Forced removal: prefix state needed. This happens in the `Solver` class.
* Skip solve if already satisfied: prefix state needed. This happens in the `Solver` class.

### Explicit package installs

These commands do not need a solver because the requested packages are expressed with a direct
URL or path to a specific tarball. Instead of a `MatchSpec`, we already have a
`PackageRecord`-like entity! For this to work, all the requested packages neeed to be URLs or paths.
They can be typed in the command line or in a text file including a `@EXPLICIT` line.

Since the solver is not involved, the dependencies of the explicit package(s) are not processed
at all. This can leave the environment in an _inconsistent state_, which can be fixed by
running `conda update --all`, for example.

Explicit installs are taken care of by the [`explicit`][conda.misc:explicit] function.

### Cloning an environment

`conda create` has a `--clone` flag that allows you to create a fully working copy of an
existing environment. This is needed because you cannot just copy (or rename) an environment
using the usual means (`cp`, `mv` or your favorite file manager): this will break your
environment! Conda _environments_ are _not_ relocatable; some files might contain hardcoded
paths to existing files in the original location, and those references will break with a
rename. You can create a new environment anywhere you want, but once created they shall not
change locations.

The [`clone_env`][conda.misc:clone_env] function implements this functionality. It essentially
takes the source environment, generates the URLs for each installed packages (filtering
`conda`, `conda-env` and their dependencies) and passes the list of URLs to `explicit()`. If
the source tarballs are not in the cache anymore, it will query the index for the best possible
match for the current channels. As such, there's a slim chance that the copy is not exactly a clone
of the original environment.

### History rollback

`conda install` has a `--revision` flag, which allows you to revert the state of the environment
to a previous one. This is done through the `History` file, but its
[current implementation][conda.plan:revert_actions] can be considered broken. Once fixed,
we will cover it in detail.

<!-- TODO: Write --revision docs once fixed -->

### Forced removals

Similar to explicit installs, you can remove a package without performing a full solve. If
`conda remove` is invoked with `--force`, the specified package(s) will be removed directly, without
analyzing their dependency tree and pruning the orphans. This can only happen after querying the
active prefix for the installed packages, so it is [handled][conda.core.solve:force_remove]
in the `Solver` class. This part of the logic returns the list of `PackageRecord` objects
already found in the `PrefixData` list after filtering out the ones that should be removed.

### Skip solve if already satisfied

`conda install` and `update` have a rather obscure flag: `-S, --satisfied-skip-solve`:

> Exit early and do not run the solver if the requested specs are satisfied. Also skips
> aggressive updates as configured by 'aggressive_update_packages'. Similar to the default
> behavior of 'pip install'.

This is also [implemented][conda.core.solve:satisfied_skip_solve] at the `Solver` level,
because we also need a `PrefixData` instance. It essentially checks if all of the passed `MatchSpec`
objects can match a `PackageRecord` already in prefix. If that's the case, we return the installed
state as is. If not, we proceed for the full solve.

(details_solve_final_state)=

## Details of `Solver.solve_final_state()`

This is were most of the intricacies of the `conda` logic are defined. In this step, the
configuration, command line flags, user-requested specs and prefix state are aggregated to query
the current index for the best match.

The aggregation of all those state bits will result in a list of `MatchSpec` objects. While it's
easy to establish which package names will make it to the list, deciding which version and build
string constrains the specs carry is a bit more involved.

This is currently implemented in the `conda.core.solve.Solver` class. Its main goal is to
populate the `specs_map` dictionary, which maps package names (`str`) to `MatchSpec` objects.
This happens at the beginning of the `.solve_final_state()` method. The full details of the
`specs_map` population are covered in the
{ref}`solver state technical specification <techspec_solver_state>`, but here's a little map
of what submethods are involved:

1. Initialization of the `SolverStateContainer`: Often abbreviated as `ssc`, it's a helper
   class to store some state across attempts (remember there are several retry loops). Most
   importantly, it stores two key attributes (among others):
    * `specs_map`: same as above. This is where it lives across solver attempts.
    * `solution_precs`: a list of `PackageRecord` objects. It stores the solution returned by
      the SAT solver. It's always initialized to reflect the installed packages in the target
      prefix.
2. `Solver._collect_all_metadata()`: Initializes the `specs_map` with the specs found in the
   history or with the specs corresponding to the installed records. This method delegates to
   `Solver._prepare()`. This initializes the index by fetching the channels and reducing it.
   Then, a `conda.resolve.Resolve` instance is created with that index. The index is stored in
   the `Solver` instance as `._index` and the `Resolve` object as `._r`. They are also kept
   around in the `SolverStateContainer`, but as public attributes: `.index` and `.r`,
   respectively.
3. `Solver._remove_specs()`: If `conda remove` was called, it removes the relevant specs from
   `specs_map`.
4. `Solver._add_specs()`: For all the other `conda` commands (`create`, `install`, `update`), it
   adds (or modifies) the relevant specs to `specs_map`. This is one of the most complicated pieces
   of logic in the class!

```{admonition} Check the other parts of the Solver API
You can check the rest of the Solver API {ref}`here <solver_api_transactions>`.
```

At this point, the `specs_map` is adequately populated and we can call the SAT solver wrapped by
the `conda.resolve.Resolve` class. This is done in `Solver._run_sat()`, but this method does some
other things before actually solving the SAT problem:

* Before calling `._run_sat()`, inconsistency analysis is performed via
  `Solver._find_inconsistent_packages`. This will preemptively remove certain `PackageRecord`
  objects from `ssc.solution_precs` if `Resolve.bad_installed()` determined they were causing
  inconsistencies. This actually runs a series of small solves to check that the installed
  records form a satisfiable set of clauses. Those that prevent that solution from being found
  are annotated as such and ignored during the real solve later.
* Make sure the requested package names are available in the index.
* Anticipate and minimize potentially conflicting specs. This happens in a `while` loop fed by
  `Resolve.get_conflicting_specs()`. If a spec is found to be conflicting, it is _neutered_: a new
  `MatchSpec` object is created, but without version and build string constrains (e.g.
  `numpy >=1.19` becomes just `numpy`). Then, `Resolve.get_conflicting_specs()` is called again,
  and the loop continues until convergence: the list of conflicts cannot be reduced further, either
  because there are no conflicts left or because the existing conflicts cannot be resolved by
  constrain relaxation.
* Now, the SAT solver is called. This happens via `Resolve.solve()`. More on this below.
* If the solver failed, then `UnsatisfiableError` is raised. Depending on which attempt we are on,
  `conda` will try again with non-frozen installed packages or a different repodata, or it will give
  up and analyze the conflict cause core. This will be detailed later.
* If the solver succeeded, some bookkeeping needs to be done:
  * Neutered specs that happened to be in the history are annotated as such.
  * Inconsistent packages are added back to the solution, including potential orphans.
  * Constrain analysis is run via `Solver.get_constrained_packages()` and
    `Solver.determine_constricting_specs()` to help the user understand why some packages were not
    updated.

We are not done yet, though. After `Solver._run_sat()`, we still need to run the post-solver logic!
After the solve, the final list of `PackageRecord` objects might still change if certain modifiers
are set. This is handled in the `Solver._post_sat_handling()`:

* `--no-deps` (`DepsModifier.NO_DEPS`): Remove dependencies of the explicitly requested packages
  from the final solution.
* `--only-deps` (`DepsModifier.ONLY_DEPS`): Remove explicitly requested packages from the final
  solution but leave their dependencies. This is done via
  `PrefixGraph.remove_youngest_descendant_nodes_with_specs()`.
* `--update-deps` (`UpdateModifier.UPDATE_DEPS`): This is the most interesting one. It actually
  runs a second solve (!) where the user-requested specs are the originally requested specs plus
  their (now determined) dependencies.
* `--prune`: Removes orphan packages from the solution.

```{admonition} The Solver also checks for Conda updates

Interestingly, the Solver API is also responsible of checking if new `conda` versions are available
in the configured channels. This is done here to take advantage of the fact that the index has been
already built for the rest of the class.
```

## Details of `conda.resolve.Resolve`

This is the class that actually wraps the SAT solver. `conda.core.solve.Solver` is a higher level
API that configures the solver _request_ and prepares the transaction. The actual solution is
computed in this other module we are discussing now.

The `Resolve` object will mostly receive two arguments:

* The fetched `index`, as processed by `conda.index.get_index()`.
* The configured `channels`, so _channel priority_ can be sorted out.

It will also hold certain state:

* The `index` will be grouped by name under a `.groups` dictionary (`str`, `[PackageRecord]`). Each
  group is later sorted so newer packages are listed first, helping reduce the index better.
* Another dictionary of `PackageRecord` groups will be created, keyed by their `track_features`
  entries, under the `.trackers` attribute.
* Some other dictionaries are initialized as caches.

The main methods in this class are:

* `bad_installed()`: This method uses a series of small solves to check if the installed packages
  are in a consistent state. In other words, if all the `PackageRecord` entries were expressed as
  `MatchSpec` objects, would the environment be solvable?
* `get_reduced_index()`: This method takes a full index and trims out the parts that are not
  necessary for the current request, thus reducing the solution space and speeding up the solver.
* `gen_clauses()`: This instantiates and configures the `Clauses` object, which is the real SAT
  solver wrapper. More on this later.
* `solve()`: The main method in the `Resolve` class. It will be discussed in the next section.
* `find_conflicts()`: If the solver didn't succeed, this method performs a conflict analysis to find
  the most plausible explanation for the current conflicts. It essentially relies on
  `build_conflict_map()` to "find the common dependencies that might be the cause of conflicts".
  `conda` can spend a lot of time in this method.

```{admonition} Disabling conflict analysis
Conflict analysis can be disabled through the `context.unsatisfiable_hints` options, but
unfortunately that gets in the way of conda's iterative logic. It will shortcut earlt on the chain
of attempts and prevent the solver from trying less constrained specs. This is a part of the logic
that should be improved.
```

### `Resolve.solve()`

WIP

### The `Clauses` object wraps the SAT solver

WIP

### Solving the SAT problem

WIP


Once the solver receives the list of specs it needs to resolve, we can consider it will do some
magic and, eventually, either:

* Succeed and return a list of `PackageRecord` objects: those entries in the index that match
  our request. More on this in the next section.
* Fail with an `UnsatisfiableError`. The details of this error are gathered through a rather
  expensive function that tries to recover _why_ the request is unsatisfiable. This is done in the
  [`build_conflict_map` function][conda.resolve:build_conflict_map].



### Back to `conda` packages... or not

WIP




<!-- Links -->
[conda_package_spec]: https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications
[conda_package_naming]: https://docs.conda.io/projects/conda-build/en/latest/concepts/package-naming-conv.html
[conda.models.records:PackageRecord]: https://github.com/conda/conda/blob/4.11.0/conda/models/records.py#L242
[conda.models.match_spec:MatchSpec]: https://github.com/conda/conda/blob/4.11.0/conda/models/match_spec.py#L73
[conda.misc:explicit]: https://github.com/conda/conda/blob/4.11.0/conda/misc.py#L52
[conda.misc:clone_env]:https://github.com/conda/conda/blob/4.11.0/conda/misc.py#L187
[conda.plan:revert_actions]: https://github.com/conda/conda/blob/4.11.0/conda/plan.py#L279
[conda.core.solve:force_remove]: https://github.com/conda/conda/blob/4.11.0/conda/core/solve.py#L239-L245
[conda.core.solve:satisfied_skip_solve]: https://github.com/conda/conda/blob/4.11.0/conda/core/solve.py#L247-L256
