# conda-runtime-updater

`conda-runtime-updater` is the transaction coordinator installed inside the
managed prefix of the conda runtime.

It has no user-facing subcommand. For root-prefix conda updates, it coordinates
the stamped outer executable with conda's existing pre-solve and post-command
hooks. It depends on conda and does not depend on conda-ship.

The pre-solve hook runs only when the target prefix is conda's root prefix and
the requested specs include `conda`, or when the operation is a root `--all`
update. Environment updates do not affect the outer executable.

For a directly managed runtime, the plugin checks and stages the outer update,
lets conda complete the inner transaction, then applies the staged executable.
It holds the runtime update lock across both layers. An interactive command
asks for approval. JSON mode and `--yes` use conda's existing noninteractive
behavior. The hook pins the inner `conda` package to the conda version bundled
by the current or staged outer runtime while preserving unrelated configured
pins. A runtime-only `.postN` suffix does not change the inner conda version.
Matching root updates reject `--no-pin` because it would bypass that
coordination. Dry runs read the local runtime record and apply its current
conda pin without checking, staging, or locking an outer update.

For an externally managed runtime, an available outer update stops the inner
transaction and reports the instruction recorded by its delivery integration.
The package manager can replace the executable before the conda update is
retried.

The plugin discovers update state only through the runtime's
`.<runtime>.json` record. It invokes the stamped executable's version-one local
helper actions and does not add a daemon, service, receipt, or updater command.
If the inner transaction fails, the old executable remains usable. The next
runtime invocation and update attempt recover or discard the interrupted
state.

The post-command hook checks for newer runtimes through conda-ship 0.10.0's
advisory probe. Interactive commands check online at most once per day and use
cached repodata offline or after network failures. A missing cache or an older
executable without the probe leaves the command silent. Notifications do not
stage updates, take the update lock, or run for quiet, JSON, dry-run, and
noninteractive commands.

Set `CONDA_PLUGINS_RUNTIME_UPDATE_NOTIFICATIONS=false` to disable runtime notifications.
`CONDA_OFFLINE=true` keeps checks offline. The packaged
`condarc.d/conda-runtime-updater.yaml` sets `notify_outdated_conda: false` to
suppress conda's generic update warning. This default applies wherever the
updater package is installed, including Windows. It does not disable update
commands. User configuration and `CONDA_NOTIFY_OUTDATED_CONDA=true` can
restore the generic warning.

The plugin is packaged separately from conda and installed only in the managed
prefixes of conda binaries. Its source lives in the [conda repository](https://github.com/conda/conda).

Run the focused tests with
`pixi run --manifest-path runtime/updater/pyproject.toml --locked test`.
The `lint` and `format-check` tasks check the same workspace.

The development package version is `0.2.0`. Release builds set
`CONDA_RUNTIME_VERSION` to the conda release version before running
`rattler-build build --recipe runtime/recipes/conda-runtime-updater/recipe.yaml
--channel conda-forge`. The recipe updates package metadata inside its temporary
source copy, leaving the checkout unchanged.
