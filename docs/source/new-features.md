# New features to try

This page contains recent additions to `conda` worth your attention, including features still in beta that we'd love your feedback on. For the full list of changes across releases, see the **{doc}`release-notes`**.

:::{container} conda-feature-legend

**Stage legend**

{bdg-success}`Stable` — Recommended for production use. Some features require configuration.

{bdg-warning}`Beta` — Opt in to test, not recommended for production. We want your feedback!

:::
---
## Faster solves: conda-rattler-solver is now conda's default solver

::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-stable

{bdg-light}`Default in conda 26.10 or later` &nbsp; {bdg-success}`Stable`

Starting with **conda 26.10**, **conda-rattler-solver** replaces conda-libmamba-solver as **conda's default solver**, delivering faster dependency resolution, especially for medium and large environments.

`conda-rattler-solver` also natively supports newer conda capabilities, including {doc}`Installing packages from PyPI with conda </user-guide/tasks/install-packages-from-pypi>`. This transition also paves the way for removing libmamba and classic solvers from the default conda installation, reducing its size and dependencies.

:::{dropdown} How to manage your solver
:animate: fade-in-slide-down

Check your configured solver:
```bash
conda config --show solver
```
To change your solver configuration:
```bash
conda config --set solver libmamba
```
Remove the override to use conda's default solver:
```bash
conda config --remove-key solver
```
:::

For details about available solvers and configuration options, see **{doc}`Solvers </user-guide/concepts/solvers>`**.

If you encounter problems, please **[report an issue on GitHub](https://github.com/conda/conda/issues/new/choose)**.


::::


## Native Windows ARM64 support

::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-stable

{bdg-light}`Available in conda 26.9 or later` &nbsp; {bdg-success}`Stable`

Conda has introduced native support for `win-arm64`, the Windows on ARM platform, and can now resolve and install packages natively for the win-arm64 architecture. This means you no longer need to rely on workarounds like WSL2, x86-64 emulation, or manual compilation to run your Python data science toolchain on ARM hardware.

:::{dropdown} How to use it
:animate: fade-in-slide-down

Specify the `win-arm64` target platform when creating an environment:

```bash
conda create --platform win-arm64 --name myenv-arm64 python
```

Select `win-arm64` as your configured target platform:

```bash
conda config --set subdir win-arm64
```
Restore automatic platform detection:

```bash
conda config --remove-key subdir
```

:::

::::
## Exclude newer packages from solves and searches

::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-stable

{bdg-light}`Available in conda 26.9 or later` &nbsp; {bdg-success}`Stable`

The `--exclude-newer` flag excludes package records with timestamps after a configured cutoff from environment solves. A configured `exclude_newer` policy also filters `conda search` results. This setting can be used to:

 - avoid pulling in brand-new package releases before regressions or malicious versions have had time to surface and be pulled
 - support reproducible resolution with time-based cutoffs
 - reduce the number of packages the solver considers while creating your environment, causing faster solve times

:::{dropdown} Usage and limitations
:animate: fade-in-slide-down

### Usage

Use `--exclude-newer` with `conda create`, `conda install`, or `conda update`:

```bash
conda install --exclude-newer 2026-08-01 scipy
```

You can also configure a global cutoff, per-channel overrides, and per-package exceptions in your `.condarc`:

```yaml
# Global cutoff
exclude_newer: 7d

# Per-channel overrides
channel_settings:
  - channel: conda-forge
    exclude_newer: 3d

# Per-package overrides
exclude_newer_package:
  openssl: false
  ca-certificates: false
  numpy: 30d
```

Package overrides take precedence over channel overrides, which take precedence over the global cutoff.

Accepted values include durations (`7d`, `3d12h`, `1w`), ISO 8601 durations (`P7D`), RFC 3339 timestamps, and dates (`2026-04-01`).

### Timestamp behavior and limitations

Conda prefers the channel-provided `indexed_timestamp`, which is intended to record when a package first became available in the channel index. If it is absent or zero, conda falls back to the builder-controlled `timestamp`, which records build time rather than publication time. If a package does not have a useable timestamp, conda cannot compare the package against the exclusion cutoff, so it remains eligible for installation.

For artifacts predating [CEP 47](https://conda.org/learn/ceps/cep-0047/#channel-server-requirements), channels may seed `indexed_timestamp` from build timestamps or other historical signals. These values may not reflect the exact time a package became available.

This fallback can still reduce exposure to newly built malicious packages when build timestamps are accurate, allowing time for detection and removal. However, it does not provide a reliable cooldown period after publication:

- An old build uploaded today may pass the cutoff.
- A malicious publisher can backdate the build timestamp.
- A cutoff may delay legitimate security fixes.

**Timestamp filtering does not guarantee package safety.** It can support reproducible resolution, but does not guarantee an exact reconstruction of a channel's historical state.

:::

For more information, see **{ref}`Installing packages with a timestamp cutoff <installing-packages-with-an-upload-cutoff>`**.

::::

## Install packages from PyPI with `conda install`

::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-stable

{bdg-light}`Available in conda 26.9 or later` &nbsp; {bdg-success}`Stable`

The new conda-pypi plugin lets you install supported pure Python wheels from PyPI natively with the `conda install` command. Conda resolves dependencies together, without a separate `pip install` step that can introduce conflicts and make environments harder to reproduce. Once installed, these packages are fully managed by conda: they appear in `conda list`, are captured by `conda export`, and can be removed with `conda remove`.

PyPI packages are made available through the free `conda-pypi` channel, which you can now also **[browse on Anaconda.org](https://anaconda.org/channels/conda-pypi)** to discover available packages.


:::{dropdown} How to try it
:animate: fade-in-slide-down

The `conda-rattler-solver` plugin is required. Check your configured solver with `conda config --show solver`. If it isn't `rattler`, select it explicitly:
```bash
conda config --set solver rattler
```
Add the `conda-pypi` channel after your conda channels:
```bash
conda config --append channels conda-pypi
```
Search for a package in the channel, then install it:
```bash
conda search conda-pypi::<package-name>
conda install <package-name>
```
**Note:** Only pure Python wheels from public PyPI are supported in this workflow. Wheels come directly from PyPI and aren't reviewed before they're added to the channel.
:::

For more details and limitations, see **{doc}`Installing packages from PyPI with conda </user-guide/tasks/install-packages-from-pypi>`**.
::::

## Reproducible environments with multi-platform lockfiles

::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-stable

{bdg-light}`Available in conda 26.5 or later` &nbsp; {bdg-success}`Stable`


Conda can export environments to lockfiles and create environments from them. A lockfile pins exact package versions and builds, so conda recreates the environment without solving again. A single multi-platform lockfile can contain resolved packages for Linux, macOS, and Windows.

The `conda-lock.yaml` and `pixi.lock` formats are supported natively. No additional tools or plugins are required.

:::{dropdown} How to use it
:animate: fade-in-slide-down

Export a lockfile for an existing environment:

```bash
conda export --name myenv --file conda-lock.yaml
```

Create an environment from the lockfile:

```bash
conda create --name myenv-copy --file conda-lock.yaml
```

Export a lockfile that covers multiple platforms:

```bash
conda export --name myenv --file conda-lock.yaml \
  --platform linux-64 \
  --platform osx-arm64 \
  --platform win-64
```

:::

For more details, see **[Multi-platform lockfiles](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html#multi-platform-lockfiles)**.

::::
