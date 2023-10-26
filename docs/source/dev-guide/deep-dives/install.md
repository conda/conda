<!--
Author: Jaime Rodríguez-Guerra <@jaimergp>, Quansight Labs.

Some resources that helped draft this document:
* https://speakerdeck.com/asmeurer/conda-internals
* https://www.anaconda.com/blog/understanding-and-improving-condas-performance
-->

# `conda install`

In this document we will explore what happens in Conda from the moment a user types their
installation command until the process is finished successfully. For the sake of completeness,
we will consider the following situation:

* The user is running commands on a Linux x64 machine with a working installation of Miniconda.
* This means we have a `base` environment with `conda`, `python`, and their dependencies.
* The `base` environment is already preactivated for Bash. For more details on activation, check
  {ref}`deep_dive_activation`.

Ok, so... what happens when you run `conda install numpy`? Roughly, these steps:

1. Command line interface
    * `argparse` parsers
    * Environment variables
    * Configuration files
    * Context initialization
    * Delegation of the task
2. Fetching the index
    * Retrieving all the channels and platforms
    * A note on channel priorities
3. Solving the install request
    * Requested packages + prefix state = list of specs
    * Index reduction (sometimes)
    * Running the solver
    * Post-processing the list of packages
4. Generating the transaction and the corresponding actions
5. Download and extraction
6. Integrity verification
7. Linking and unlinking files
8. Post-linking and post-activation tasks

```{figure} /img/conda-install-deep-dive.png
:name: conda-install-figure

This figure shows the different processes and objects involved in handling a simple `conda install`
command.
```

## Command line interface

<!-- This might be better in a separate deep-dive for the command line alone -->

First, a quick note on an implementation detail that might be not obvious.

When you type `conda install numpy` in your terminal, Bash takes those three words and looks for a
`conda` command to pass a list of arguments `['conda', 'install', 'numpy']`. Before finding the
`conda` executable located at `CONDA_HOME/condabin`, it probably finds the shell function
defined [here][conda_shell_function]. This shell function runs the activation/deactivation
logic on the shell if requested, or delegates over to the actual Python entry-points otherwise.
This part of the logic can be found in [`conda.shell`][conda.shell].

Once we are running the Python entry-point, we are in the [`conda.cli`][conda.cli]
realm. The function called by the entry point is [`conda.cli.main:main()`][conda.cli.main:main].
Here, another check is done for `shell.*` subcommands, which generate the shell initializers you see
in `~/.bashrc` and others. If you are curious where this happens, it's
[`conda.activate`][conda.activate].

Since our command is `conda install ...`, we still need to arrive somewhere else. You will notice
that the rest of the logic is delegated to `conda.cli.main:_main()`, which will invoke the parser
generators, initialize the context and loggers, and, eventually, pass the argument list over to
the corresponding command function. These four steps are implemented in four functions/classes:

1. [`conda.cli.conda_argparse:generate_parser()`][conda.cli.conda_argparse:generate_parser]:
   This uses `argparse` to generate the CLI. Each subcommand is initialized in separate functions.
   Note that the command line options are not generated dynamically from the `Context` object, but
   annotated manually. If this is needed (e.g. `--repodata-fn` is exposed in `Context.repodata_fn`),
   the `dest` variable of each CLI option should
   [match the target attribute in the context object][context_match].
2. [`conda.base.context.Context`][context_init]: This object stores the configuration options
   in `conda` and will be initialized taking into account, among other things, the arguments
   parsed in the step above. This is covered in more detail in a separate deep dive:
   {ref}`deep_dive_context`.
3. [`conda.gateways.logging:initialize_logging()`][initialize_logging]:
   Not too exciting and easy to follow. This part of the code base is more or less self-explanatory.
4. [`conda.cli.conda_argparse:do_call()`][conda.cli.conda_argparse:do_call]: The argument parsing
   will populate a `func` value that contains the import path to the function responsible for that
   subcommand. For example, `conda install` is [taken care of][conda_install_delegation] by
   [`conda.cli.command.main_install`][conda.cli.command.main_install]. By design, all the modules reported by `func`
   must contain an `execute()` function that implements the command logic. `execute()` takes the
   parsed arguments and the parser itself as arguments. For example, in the case of `conda install`,
   `execute()` only [redirects][conda_main_install_delegation] to a certain mode in
   [`conda.cli.install:install()`][conda.cli.install:install].

Let's go take a look at that module now. [`conda.cli.install:install()`][conda.cli.install:install]
implements the logic behind `conda create`, `conda install`, `conda update` and `conda remove`.
In essence, they all deal with the same task: changing which packages are present in an environment.
If you go and read that function, you will see there are several lines of code handling diverse
situations (new environments, clones, etc.) before we arrive to the next section. We will not discuss
them here, but feel free to explore [that section][conda_cli_install_presolve_logic].
It's mostly ensuring that the destination prefix exists, whether we are creating a new environment
and massaging some command line flags that would allow us to skip the solver (e.g. `--clone`).

```{admonition} More information on environments
Check the concepts for {ref}`concepts-conda-environments`.
```

<!-- TODO: Maybe we do want to explain those checks? -->

## Fetching the index

At this point, we are ready to start doing some work! All of the previous code was telling us what to
do, and now we know. We want `conda` to _install_  `numpy` on our `base` environment. The first thing
we need to know is where we can find packages with the name `numpy`. The answer is... the channels!

Users download packages from `conda` channels. These are normally hosted at `anaconda.org`. A
channel is essentially a directory structure with these elements:

```
<channel>
├── channeldata.json
├── index.html
├── <platform> (e.g. linux-64)
│   ├── current_repodata.json
│   ├── current_repodata.json.bz2
│   ├── index.html
│   ├── repodata.json
│   ├── repodata.json.bz2
│   ├── repodata_from_packages.json
│   └── repodata_from_packages.json.bz2
└── noarch
    ├── current_repodata.json
    ├── current_repodata.json.bz2
    ├── index.html
    ├── repodata.json
    ├── repodata.json.bz2
    ├── repodata_from_packages.json
    └── repodata_from_packages.json.bz2
```

```{admonition} More info on Channels
You can find some more user-oriented notes on Channels at {ref}`concepts-channels` and
{ref}`repo-si`. If you are interested in more technical details, check the corresponding
[documentation pages at conda-build][conda_build_channels].
```

The important bits are:

* A channel contains one or more platform-specific directories (`linux-64`, `osx-64`, etc.),
  plus a platform-agnostic directory called `noarch`. In `conda` jargon, these are also
  referred to as channel _subdirs_. Officially, the `noarch` subdirectory is enough to make it
  a `conda` channel; e.g. no platform subdirectory is necessary.
* Each _subdir_ contains at least a `repodata.json` file: a gigantic dictionary with _all_ the
  metadata for each package available on that platform.
* In most cases, the same subdirs also contain the `*.tar.bz2` files for each of the published
  packages. This is what `conda` downloads and extracts once solving is complete. The anatomy
  of these files is well defined, both in content and naming structure. See
  {ref}`concept-conda-package`, {ref}`package_metadata` and/or [Package naming
  conventions][conda_build_package_names] for more details.

<!-- TODO: Check why and reasons for this file to exist -->

Additionally, the channel's main directory might contain a `channeldata.json` file, with channel-wide
metadata (this is not specific per platform). Not all channels include this, and in general
it is not currently something that is commonly utilized.

Since conda's philosophy is to keep all packages ever published around for reproducibility,
`repodata.json` is always growing, which presents a problem both for the download itself and the
solver engine. To reduce download times and bandwidth usage, `repodata.json` is also served as a
BZIP2 compressed file, `repodata.json.bz2`. This is what most `conda` clients end up downloading.

```{admonition} Note on 'current_repodata.json'

More _repodatas_ variations can be found in some channels, but they are always reduced versions
of the main one for the sake of performance. For example, `current_repodata.json` only contains
the most recent version of each package, plus their dependencies. The rationale behind this
optimization trick can be found [here][current_repodata_details].
```

So, in essence, fetching the channel information means it can be expressed in pseudo-code like this:

```python
platform = {}
noarch = {}
for channel in reversed(context.channels):
    platform_repodata = fetch_extract_and_read(
        channel.full_url / context.subdir / "repodata.json.bz2"
    )
    platform.update(platform_repodata)
    noarch_repodata = fetch_extract_and_read(
        channel.full_url / "noarch" / "repodata.json.bz2"
    )
    noarch.update(noarch_repodata)
```

Note that these dictionaries are keyed by _filename_, so higher priority channels will overwrite
entries with the exact same filename (e.g. `numpy-1.19-py36h87ha43_0.tar.bz2`). If they don't have
the same _filename_ (e.g., same version and build number but different hash), this ambiguity will
be resolved later in the solver, taking into account the channel priority mode.

In this example, `context.channels` has been populated through different, cascading mechanisms:

* The default settings as found in `~/.condarc` or equivalent.
* The `CONDA_CHANNELS` environment variable (rare usage).
* The command-line flags, such as `-c <channel>`, `--use-local` or `--override-channels`.
* The channels present in a command-line {ref}`spec <build-version-spec>`. Remember that users can
  say `channel::numpy` instead of simply `numpy` to require that numpy comes from that specific
  channel. That means that the repodata for such channel needs to be fetched, too!

The items in `context.channels` are supposed to be `conda.models.channels.Channel` objects, but
the Solver API also allows strings that refer to their name, alias or full URL. In that case,
you can use `Channel` objects to parse and retrieve the full URL for each subdir using the
`Channel.urls()` method. Several helper functions can be found in `conda.core.index`, if
needed.

Sadly, `fetch_extract_and_read()` does not exist as such, but as a combination of objects. The
main driving function is actually [`get_index()`][conda.core.index:get_index], which passes the
channel URLs to `fetch_index`, a wrapper that delegates directly to
`conda.core.subdir_data.SubdirData` objects. This object implements caching, authentication,
proxies and other things that complicate the simple idea of "just download the file, please".
Most of the logic is in `SubdirData._load()`, which ends up calling
`conda.core.subdir_data.fetch_repodata_remote_request()` to process the request. Finally,
`SubdirData._process_raw_repodata_str()` does the parsing and loading.

Internally, the `SubdirData` stores all the package metadata as a list of `PackageRecord`
objects. Its main usage is via `.query()` (one result at a time) or `.query_all()` (all
possible matches). These `.query*` methods accept spec strings (e.g. `numpy =1.14`),
`MatchSpec` and `PackageRecord` instances. Alternatively, if you want _all_ records with no
queries, use `SubdirData.iter_records()`.

(index_reduction_tricks)=

```{admonition} Tricks to reduce the size of the index

`conda` supports the notion of trying with different versions of the index in an effort to minimize
the solution space. A smaller index means a faster search, after all! The default logic starts with
`current_repodata.json` files in the channel, which contain only the latest versions of each package
plus their dependencies. If that fails, then the full `repodata.json` is used. This happens _before_
the `Solver` is even invoked.

The second trick is done within the solver logic: an informed index reduction. In essence, the
index (whether it's `current_repodata.json` or full `repodata.json`) is pruned by the solver,
trying to keep only the parts that it anticipates will be needed. More details can be found on
[the `get_reduced_index` function][conda.core.index:get_reduced_index]. Interestingly, this
optimization step also takes longer the bigger the index gets.
```

### Channel priorities

`context.channels` returns an `IndexedSet` of `Channel` objects; essentially a list of unique
items. The different channels in this list can have overlapping or even conflicting information
for the same package name. For example, `defaults` and `conda-forge` will for sure contain
packages that fullfil the `conda install numpy` request. Which one is chosen by `conda` in this
case? It depends on the `context.channel_priority` setting: From the help message:

> Accepts values of 'strict', 'flexible', and 'disabled'. The default value is 'flexible'. With
> strict channel priority, packages in lower priority channels are not considered if a package
> with the same name appears in a higher priority channel. With flexible channel priority, the
> solver may reach into lower priority channels to fulfill dependencies, rather than raising an
> unsatisfiable error. With channel priority disabled, package version takes precedence, and
> the configured priority of channels is used only to break ties.

In practice, `channel_priority=strict` is often the recommended setting for most users. It's faster
to solve and causes fewer problems down the line. Check more details
{ref}`here <concepts-performance-channel-priority>`.

## Solving the install request

At this point, we can start asking the solver things. After all, we have loaded the
channels into our index, building the catalog of available packages and versions we can
install. We also have the command line instructions and configurations needed to customize the
solver request. So, let's just do it: "Solver, please install numpy on this prefix using these
channels as package sources".

The details are complicated, but in essence, the `Solver` will:

1. Express the requested packages, command line options and prefix state as `MatchSpec` objects
2. Query the index for the best possible match that satisfy those constraints
3. Return a list of `PackageRecord` objects

The full details are covered in {doc}`solvers` if you are curious. Just keep in mind that
point (1) is conda-specific, while (2) can be tackled, in principle, by any SAT solver.

(solver_api_transactions)=
## Generating the transaction and the corresponding actions

The Solver API defines three public methods:

* `.solve_final_state()`: this is the core function, described in the section above. Given some
  input state, it returns an `IndexedSet` of `PackageRecord` objects that reflect what the final
  state of the environment should look like. This is the largest method, and its details are
  fully covered {ref}`here <details_solve_final_state>`.
* `.solve_for_diff()`: this method takes the final state and diffs it with the current state of the
  environment, discovering which old records need to be removed, and which ones need to be added.
* `.solve_for_transaction()`: this method takes the diff and creates a `Transaction` object for this
  operation. This is what the main CLI logic expects back from the solver.

So what is a `Transaction` object and why is it needed? [Transactional actions][transaction_PR]
were introduced in conda 4.3. They seem to be the last iteration of a set of changes designed to
check whether `conda` would be able to download and link the needed packages (e.g. check that
there is enough space on disk, whether the user has enough permissions for the target paths, etc.).
For more info, refer to PRs [#3571][pr3571], [#3301][pr3301], and [#3034][pr3034].

The transaction is essentially a set of `action` objects. Each action is allowed to run some
checks to determine whether it can be executed successfully. If that's not the case, the failed
checks will signal the parent transaction that the whole operation needs to be aborted and
rolled back to leave things in the state they were before running that `conda` command. It is also
responsible for some of the messages you will see in the CLI output, like the reports of what will
be installed, updated or removed.

```{admonition} Transactions and parallelism

Since the transaction object knows about all the actions that need to happen, it also enables
parallelism for verifying, downloading and (un)linking tasks. The level of parallelism
can be changed through the following `context` settings:

* `default_threads`
* `verify_threads`
* `execute_threads`
* `repodata_threads`
* `fetch_threads`
```

There's only one class of transaction in `conda`:
[`LinkUnlinkTransaction`][conda.core.link:UnlinkLinkTransaction]. It only accepts one input parameter:
a list of `PrefixSetup` objects, which are just `namedtuple` objects with the followiing fields.
These are populated by `Solver.solve_for_transaction` after running `Solver.solve_for_diff`:

* `target_prefix`: the environment path the command is running on.
* `unlink_precs`: `PackageRecord` objects that need to be unlinked (removed).
* `link_precs`: `PackageRecord` objects that need to be linked (added).
* `remove_specs`: `MatchSpec` objects that need to be marked as removed in the history (the user
  asked for these packages to be uninstalled).
* `update_specs`: `MatchSpec` objects that need to be marked as added in the history (the user
  asked for these packages to be installed or updated).
* `neutered_specs`: `MatchSpec` objects that were already in history but had to be relaxed in order
  to avoid solving conflicts.

Whatever happens after instantiation depends on the content of these `PrefixSetup` objects.
Sometimes, the transaction results in no actions (see the [`nothing_to_do`][nothing_to_do]
property) because the request asked by the user is already fulfilled by the current state
of the environment.

However, most of the time the transaction will involve a number of actions. This is done via two
public methods:

* `download_and_extract()`: essentially a forwarder to instantiate and call
  `ProgressiveFetchExtract`, responsible for deciding which `PackageRecords` need to be
  downloaded and extracted to the packages cache.
* `execute()`: the core logic is layed out here. It involves preparing, verifying and
  performing the rest of the actions. Among others:
    * Unlinking packages (removing a package from the environment)
    * Linking (adding a package to the environment)
    * Compiling bytecode (generating the `pyc` counterpart for each `py` module)
    * Adding entry points (generate command line executables for the configured functions)
    * Adding the JSON records (for each package, a JSON file is added to `conda-meta/`)
    * Make menu items (create shortcuts for packages featuring a JSON file under `Menu/`)
    * Remove menu items (remove the shortcuts created by that package)

It's important to notice that download and extraction happen separately from all the other actions.
This separation is important and core to the idea of what a `conda` environment is. Essentially,
when you create a new `conda` environment, you are not necessarily _copying_ files over to the target
prefix location. Instead, `conda` maintains a cache of every package ever downloaded to disk (both
the tarball and the extracted contents). To save space and speed up environment creation and
deletion, files are not copied over, but instead they are linked (usually via a hardlink). That's
why these two tasks are separated in the transaction logic: you don't need to download and extract
packages that are already in the cache; you only need to link them!

````{admonition} Transactions also drive reports

The type and number of actions can also be calculated by `_make_legacy_action_groups()`, which
returns a list of _action groups_ (one per `PrefixSetup`). Each action group is a just a dictionary
following this specification:

```
{
  "FETCH": Iterable[PackageRecord],  # estimated by `ProgressiveFetchExtract`
  "PREFIX": str,
  "UNLINK": Iterable[PackageRecord],
  "LINK: Iterable[PackageRecord],
}
```

These simpler action groups are only used for reporting, either via a processed text report
(via `print_transaction_summary`) or just the raw JSON (via `stdout_json_success`). As you can see,
they do not know anything about other types of tasks.
````

## Download and extraction

`conda` maintains a cache of downloaded tarballs and their extracted contents to save disk space
and improve the performance of environment modifications. This requires some code to check whether
a given `PackageRecord` is already present in the cache, and, if it's not, how to download the
tarball and extract its contents in a performant way. This is all handled by the
`ProgressiveFetchExtract` class, which can instantiate up to two `Action` objects for each
passed `PackageRecord`:

* `CacheUrlAction`: downloads (if remote) or copies (if local) a tarball to the cache location.
* `ExtractPackageAction`: extracts the contents of the tarball.

These two actions only take place _if_ the package is not in cache yet and if it has already been
extracted, respectively. They can also revert the changes if the transaction is aborted (either
due to an error or because the user pressed Ctrl+C).

<!-- TODO: Add "Anatomy of the conda caches" admonition-->

## Populating the prefix

When all the necessary packages have been downloaded and extracted to the cache, it is time to
start populating the prefix with the needed files. This means we need to:

1. For each package that needs to be unlinked, run the pre-unlink logic (`deactivate` and
   `pre-unlink` scripts, as well as shortcut removal, if needed) and then unlink the package files.
2. For each package that needs to be linked, create the links and run the post-link logic
   (`post-link` and `activate` scripts, as well as creating the shortcuts, if needed).

> Note that when you are updating a package version, you are actually removing the installed version
entirely and then adding the new one. In other words, an update is just unlink+link.

How is this implemented? For each `PrefixSetup` object passed to `UnlinkLinkTransaction`, a
number of `ActionGroup` namedtuples (one per task _category_) will be instantiated and grouped
together in a `PrefixActionGroup` namedtuple. These are then passed to `.verify()`. This method
will take each action, run its checks and, if all of them passed, will allow us to perform the
actual execution in `.execute()`. If one of them fails, the transaction can be aborted and
rolled back.

For all this to work, each action object follows the
[`PathAction` API contract][conda.core.path_actions:PathAction]:

```python
class PathAction:
    _verified = False

    def verify(self):
        "Run checks to assess if the action can proceed"

    def execute(self):
        "Perform the action"

    def reverse(self):
        "Undo execute"

    def cleanup(self):
        "Remove artifacts from verification, execution or reversal"

    @property
    def verified(self):
        "True if verification was run and successful"
```

Additional `PathAction` subclasses will add more methods and properties, but this is what the
transaction execution logic expects. To support all the different actions involved in populating
the prefix, the `PathAction` class tree holds quite the graph:

```
PathAction
  PrefixPathAction
    CreateInPrefixPathAction
      LinkPathAction
        PrefixReplaceLinkAction
      MakeMenuAction
      CreateNonadminAction
      CreatePythonEntryPointAction
      CreatePrefixRecordAction
      UpdateHistoryAction
    RemoveFromPrefixPathAction
      UnlinkPathAction
        RemoveLinkedPackageRecordAction
      RemoveMenuAction
  RegisterEnvironmentLocationAction
  UnregisterEnvironmentLocationAction
  CacheUrlAction
  ExtractPackageAction

MultiPathAction
  CompileMultiPycAction
    AggregateCompileMultiPycAction

```

You are welcome to read on the docstring for each of those classes to understand which each one
is doing; all of them are listed under `conda.core.path_actions`. In the following sections, we will
only comment on the most important ones.

## Linking the files in the environment

When conda _links_ a file from the cache location to the prefix location, it can actually mean
three different actions:

1. Creating a soft link
2. Creating a hard link
3. Copying the file

The difference between soft links and hard links is subtle, but important. You can find more info on
the differences elsewhere (e.g. [here][hardlinks_vs_softlinks]), but for our purposes it means that:

* Hard links are cheaper to resolve, behave like a real file, but can only link files in the same
  mount point.
* Soft links can link files across mount points, but they don't behave exactly like files (more like
  forwarders), so it's possible that they break assumptions made in certain pieces of code.

Most of the time, `conda` will try to hard link files and, if that fails, it will copy them over.
Copying a file is an expensive disk operation, both in terms of time and space, so it should be
the last option. However, sometimes it's the only way. Especially, when the file needs to be
modified to be used in the target prefix.

Ummm... what? Why would `conda` modify a file to install it? This has to do with relocatability.
When a `conda` package is created, `conda-build` creates up to three temporary environments:

* Build environment: where compilers and other build tools are installed, separate from the
  host environment to support cross-compilation.
* Host environment: where build-time dependencies are installed, together with the package you
  are building.
* Test environment: where run-time dependencies are installed, together with the package you just
  built. It simulates what will happen when a user installs the package so you can run arbitrary
  checks on your package.

When you are building a package, references to the build-time paths can leak into the content of
some files, both text and binary. This is not a problem for users who build their own packages
from source, since they can choose this path and leave the files there. However, this is almost
never true for `conda` packages. They are created in one machine and installed in another. To avoid
"path not found" issues and other problems, `conda-build` marks those packages that hold references
to the build-time paths by replacing them with placeholders. At install-time, `conda` will replace
those placeholders with the target prefix and everything works!

But there's a problem: we can't modify the files on the cache location because they might be used
across environments (with obviously different paths). In these cases, files are not linked, but
copied; the path replacement only happens on the target copy, of course!

How does `conda` know how to link a given package or, more precisely, its extracted files? All
of this is determined in the preparation routines contained in
[`UnlinkLinkTransaction._prepare()`][conda.core.link:_prepare] (more specifically, through
[`determine_link_type()`][conda.core.link:determine_link_type]), as well as
[`LinkPathAction.create_file_link_actions()`][conda.core.path_actions:create_file_link_actions].

Note that the (un)linking actions also include the execution of pre-(un)link and post-(un)link
scripts, if listed.

## Action groups and actions, in detail

Once the old packages have been removed and the new ones have been linked through the appropriate
means, we are done, right? Not yet! There's one step left: the post-linking logic.

It turns out that there's a number of smaller tasks that need to happen to make `conda` as
convenient as it is. You can find all of them listed a few paragraphs above, but we'll cover
them here, too. The execution order is determined in
[`UnlinLinkTransaction._execute`][conda.core.link:_execute].
All the possible groups are listed under [`PrefixActionGroup`][conda.core.link:PrefixActionGroup].
Their order is roughly how they happen in practice:

1. `remove_menu_action_groups`, composed of `RemoveMenuAction` actions.
2. `unlink_action_groups`, includes `UnlinkPathAction`, `RemoveLinkedPackageRecordAction`, as well
   as the logic to run the pre- and post-unlink scripts.
3. `unregister_action_groups`, basically a single `UnregisterEnvironmentLocationAction` action.
4. `link_action_groups`, includes `LinkPathAction`, `PrefixReplaceLinkAction`, as well as the logic
   to run pre- and post-link scripts.
8. `entry_point_action_groups`, a collection of `CreatePythonEntryPointAction` actions.
5. `register_action_groups`, a single `RegisterEnvironmentLocationAction` action.
6. `compile_action_groups`, several `CompileMultiPycAction` that end up aggregated as a
   `AggregateCompileMultiPycAction` for performance.
7. `make_menu_action_groups`, composed of `MakeMenuAction` actions.
9. `prefix_record_groups`, records installed packages in the environment via
   `CreatePrefixRecordAction` actions.

Let's discuss these actions groups for the command we are describing in this guide: `conda
install numpy`. The solution given by the solver says we need to:

* unlink Python 3.9.6
* link Python 3.9.9
* link numpy 1.19

This is what would happen:

1. No menu items are removed because Python 3.9.6 didn't create any.
2. Pre-unlink scripts for Python 3.9.6 would run, but in this case there are none.
3. Python 3.9.6 files are removed from the environment. This can be parallelized.
4. Post-unlink scripts are run, if any.
5. Pre-link scripts are run for Python 3.9.9 and numpy 1.19, if any.
6. Files in the Python 3.9.9 and numpy 1.19 packages are linked and/or copied to the prefix. This
   can be parallelized.
7. Entry points are created for the new packages, if any.
8. Post-link scripts are run.
9. `pyc` files are generated for the new packages.
10. The new packages are registered under `conda-meta/`.
11. The menu shortcuts are created for the new packages, if any.

Any of these steps can fail with a given exception. If that's the case, the first of those
exceptions is printed to STDOUT. Additionally, if `rollback_enabled` is properly configured in
the `context`, the transaction will be rolled back by calling the `.reverse()` method in each
action, from last to first.

If no exceptions are reported, then the actions can run their cleanup routines.

And that's it! If this command had resulted in a new environment being created, you would get a
message telling you how to activate the newly created environment.

## Conclusion

This is what happens when you type `conda install`. It might be a bit more involved than you
initially thought, but it all boils down to only some steps. TL;DR:

1. Parse arguments and initialize the context
2. Download and build the index
3. Tell the solver what we want
4. Convert the solution into a transaction
5. Verify and run each action contained in the transaction


<!-- Links and references -->
[conda_build_channels]: https://docs.conda.io/projects/conda-build/en/latest/concepts/generating-index.html
[conda_build_package_names]: https://docs.conda.io/projects/conda-build/en/latest/concepts/package-naming-conv.html
[conda_cli_install_presolve_logic]: https://github.com/conda/conda/blob/4.11.0/conda/cli/install.py#L107
[conda_install_delegation]: https://github.com/conda/conda/blob/4.11.0/conda/cli/conda_argparse.py#L775
[conda_main_install_delegation]: https://github.com/conda/conda/blob/4.11.0/conda/cli/main_install.py#L12
[conda_shell_function]: https://github.com/conda/conda/blob/4.11.0/conda/shell/etc/profile.d/conda.sh#L62-L76
[conda.activate]: https://github.com/conda/conda/blob/4.11.0/conda/activate.py
[conda.cli.conda_argparse:do_call]: https://github.com/conda/conda/blob/4.11.0/conda/cli/conda_argparse.py#L77
[conda.cli.conda_argparse:generate_parser]: https://github.com/conda/conda/blob/4.11.0/conda/cli/conda_argparse.py#L28
[conda.cli.install:install]: https://github.com/conda/conda/blob/4.11.0/conda/cli/install.py#L107
[conda.cli.main_install]: https://github.com/conda/conda/blob/4.11.0/conda/cli/main_install.py
[conda.cli.main:main]: https://github.com/conda/conda/blob/4.11.0/conda/cli/main.py#L121
[conda.cli]: https://github.com/conda/conda/tree/4.11.0/conda/cli
[conda.core.index:get_index]: https://github.com/conda/conda/blob/4.11.0/conda/core/index.py#L45
[conda.core.index:get_reduced_index]: https://github.com/conda/conda/blob/4.11.0/conda/core/index.py#L246
[conda.core.link:_prepare]: https://github.com/conda/conda/blob/4.11.0/conda/core/link.py#L266
[conda.core.link:_execute]: https://github.com/conda/conda/blob/4.11.0/conda/core/link.py#L602
[conda.core.link:determine_link_type]: https://github.com/conda/conda/blob/4.11.0/conda/core/link.py#L50
[conda.core.link:PrefixActionGroup]: https://github.com/conda/conda/blob/4.11.0/conda/core/link.py#L123
[conda.core.link:UnlinkLinkTransaction]: https://github.com/conda/conda/blob/4.11.0/conda/core/link.py#L156
[conda.core.path_actions:create_file_link_actions]: https://github.com/conda/conda/blob/4.11.0/conda/core/path_actions.py#L190
[conda.core.path_actions:PathAction]: https://github.com/conda/conda/blob/4.11.0/conda/core/path_actions.py#L61
[conda.resolve:build_conflict_map]: https://github.com/conda/conda/blob/4.11.0/conda/resolve.py#L415
[conda.shell]: https://github.com/conda/conda/tree/4.11.0/conda/shell
[context_init]: https://github.com/conda/conda/blob/4.11.0/conda/cli/main.py#L75
[context_match]: https://github.com/conda/conda/blob/4.11.0/conda/cli/conda_argparse.py#L1484
[current_repodata_details]: https://docs.conda.io/projects/conda-build/en/latest/concepts/generating-index.html#trimming-to-current-repodata
[initialize_logging]: https://github.com/conda/conda/blob/4.11.0/conda/gateways/logging.py#L162
[nothing_to_do]: https://github.com/conda/conda/blob/4.11.0/conda/core/link.py#L184
[pr3034]: https://github.com/conda/conda/pull/3034
[pr3301]: https://github.com/conda/conda/pull/3301
[pr3571]: https://github.com/conda/conda/pull/3571
[transaction_PR]: https://github.com/conda/conda/pull/3833
[hardlinks_vs_softlinks]: https://askubuntu.com/questions/108771/what-is-the-difference-between-a-hard-link-and-a-symbolic-link
