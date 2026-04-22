# Latest Features

Highlights of the most recent improvements to `conda`, organized by release.
For the full list of changes, see the {doc}`release-notes`.

---

## conda 26.3 — April 2026

:::{card}

#### Plugin origin tracking

`conda info` and diagnostics now show **which plugin registered each hook**,
making it much easier to debug conflicts when multiple plugins are installed.
+++
{bdg-info}`documentation` <span style="float:right">{fab}`github` [#15840](https://github.com/conda/conda/pull/15840)</span>
:::

:::{card}

#### conda create --file accepts environment.yaml

`conda create --file <filename>` now accepts **environment.yaml** files in
addition to `requirements.txt` and explicit exports. The environment name and
prefix are detected automatically when `--name` / `--prefix` are omitted.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15770](https://github.com/conda/conda/pull/15770)</span>
:::

:::{card}

#### Faster conda run

Environment activation is now performed **inline** instead of spawning a
separate shell subprocess, giving a measurable speed-up to every `conda run`
invocation.
+++
{bdg-success}`speed` <span style="float:right">{fab}`github` [#15672](https://github.com/conda/conda/pull/15672)</span>
:::

:::{card}

#### Smarter PackagesNotFound errors

Two new exception types — `PackagesNotFoundInChannelsError` and
`PackagesNotFoundInPrefixError` — make it clear whether a missing package
cannot be found in configured channels or in the active environment.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15653](https://github.com/conda/conda/pull/15653)</span>
:::

:::{card}

#### Pattern matching for env spec plugins

Environment specifier and exporter plugins can now declare `default_filenames`
with glob patterns (e.g. `*.conda-lock.yml`) so auto-detection works without
requiring exact filename matches.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15719](https://github.com/conda/conda/pull/15719)</span>
:::

:::{card}

#### `-f` alias for `--file`

`conda create|install -f` is now a recognized shorthand for
`conda create|install --file`, saving a few keystrokes on common workflows.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15790](https://github.com/conda/conda/pull/15790)</span>
:::

---

## conda 26.1 — January 2026

:::{card}

#### Environment disk usage

A new `--size` flag for `conda info --envs`, `conda env list`, and
`conda list` displays **disk usage** for each environment and individual
packages. Programmatic access is available via `PrefixData.size` and
`PrefixRecord.package_size()`.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15544](https://github.com/conda/conda/pull/15544)</span>
:::

:::{card}

#### conda doctor --fix

`conda doctor` can now **repair** health-check failures automatically with the
`--fix` flag, not just report them.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15530](https://github.com/conda/conda/pull/15530)</span>
:::

:::{card}

#### Programmatic config API

The new `conda.cli.condarc.ConfigurationFile` class lets Python code **read
and modify** `.condarc` files without shelling out to `conda config`.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15376](https://github.com/conda/conda/pull/15376)</span>
:::

:::{card}

#### Custom package extractors plugin hook

The new `conda_package_extractors` plugin hook lets third-party plugins
**register custom archive formats**, and package extension detection is now
driven by registered extractors rather than a hard-coded list.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15441](https://github.com/conda/conda/pull/15441)</span>
:::

:::{card}

#### Improved HTTP 403 errors

HTTP 403 (Forbidden) responses now surface **context-aware guidance** on
authentication and channel permissions instead of a bare error code.
+++
{bdg-danger}`security` <span style="float:right">{fab}`github` [#15594](https://github.com/conda/conda/pull/15594)</span>
:::

:::{card}

#### Faster startup

Context initialization is faster thanks to caching of `.condarc` file reads,
reducing repeated disk access on every conda invocation.
+++
{bdg-success}`speed` <span style="float:right">{fab}`github` [#15150](https://github.com/conda/conda/pull/15150)</span>
:::

:::{card}

#### NoChannelsConfiguredError

When solving an environment with **no channels configured**, conda now raises a
clear `NoChannelsConfiguredError` with guidance on how to add channels, rather
than failing with a cryptic solver error.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15345](https://github.com/conda/conda/pull/15345)</span>
:::

---

## conda 25.11 — November 2025

:::{card}

#### Virtual package override controls

`CondaVirtualPackage` gains three new fields — `override_entity`,
`empty_override`, and `version_validation` — giving plugin authors fine-grained
control over how virtual packages can be overridden by users.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15248](https://github.com/conda/conda/pull/15248)</span>
:::

:::{card}

#### `override_virtual_packages` in condarc

A new `override_virtual_packages` key (alias `virtual_packages`) in `.condarc`
lets users pin or override virtual package values without writing a custom
plugin.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15318](https://github.com/conda/conda/pull/15318)</span>
:::

:::{card}

#### Environment creation & modification timestamps

`PrefixData` now exposes `.created` and `.last_modified` properties so tooling
can inspect **when an environment was first created and last changed**.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15329](https://github.com/conda/conda/pull/15329)</span>
:::

:::{card}

#### conda info --json env details

`conda info --json` (and `conda env list --json`) now include an `envs_details`
field with richer per-environment metadata.
+++
{bdg-info}`documentation` <span style="float:right">{fab}`github` [#15330](https://github.com/conda/conda/pull/15330)</span>
:::

---

## conda 25.9 — September 2025

```{admonition} Channel configuration change
:class: important

As of 25.9, conda no longer hard-codes Anaconda's channels as the default.
It is now up to distribution providers (Miniforge, Miniconda, …) to
pre-configure their preferred channels. See the
[announcement](https://github.com/conda/conda/issues/14178) for details.
```

:::{card}

#### CEP-24 environment.yaml support

A new built-in `cep-24` environment spec plugin implements the updated
`environment.yml` specification from
[CEP 24](https://github.com/conda/ceps/blob/main/cep-24.md) and is enabled by
default.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15120](https://github.com/conda/conda/pull/15120)</span>
:::

:::{card}

#### conda doctor health checks

Two new health checks land in `conda doctor`: a **pinned-file format** check
and a **file locking** check, helping diagnose stubborn environment issues.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15114](https://github.com/conda/conda/pull/15114)</span>
:::

:::{card}

#### Frozen environment indicators

Environments marked as frozen (CEP 22) are now flagged with `+` in
`conda info --envs` and `conda env list` output.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15213](https://github.com/conda/conda/pull/15213)</span>
:::

:::{card}

#### Multiplatform environment export

`CondaEnvironmentExporter.multiplatform_export` enables export formats that
embed **multiple platform lock files** in a single document.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#15253](https://github.com/conda/conda/pull/15253)</span>
:::

:::{card}

#### `--environment-specifier` CLI flag

A new `--environment-specifier` (alias `--env-spec`) flag and matching
`environment_specifier` condarc key let users explicitly choose which
environment spec plugin handles a given file.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#14877](https://github.com/conda/conda/pull/14877)</span>
:::

---

## conda 25.7 — August 2025

:::{card}

#### Enhanced conda export

`conda export` is now plugin-driven and supports multiple output formats:
`environment-yaml` (default), `environment-json`, `explicit`, and
`requirements`. Format is auto-detected from the output filename when
`--output` is specified.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#14886](https://github.com/conda/conda/pull/14886)</span>
:::

:::{card}

#### Explicit env spec in conda create

`conda create/install/update` now accept **explicit environment spec files**
(e.g. `@EXPLICIT` URL lists), bringing full parity with the `conda env`
subcommands.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#14820](https://github.com/conda/conda/pull/14820)</span>
:::

:::{card}

#### Environment data model

An experimental `conda.models.environment.Environment` data model provides a
structured, programmatic representation of a conda environment for use by
plugins and tooling.
+++
{bdg-info}`documentation` <span style="float:right">{fab}`github` [#14870](https://github.com/conda/conda/pull/14870)</span>
:::

:::{card}

#### Environment consistency check

`conda doctor` gains an **environment consistency** health check that detects
broken or inconsistent package records in an environment.
+++
{bdg-warning}`user experience` <span style="float:right">{fab}`github` [#14799](https://github.com/conda/conda/pull/14799)</span>
:::

:::{card}

#### `CondaPlugin` base class

A new `CondaPlugin` base class with automatic name normalization simplifies
writing third-party plugins.
+++
{bdg-info}`documentation` <span style="float:right">{fab}`github` [#15002](https://github.com/conda/conda/pull/15002)</span>
:::

---

:::{seealso}
- {doc}`release-notes` — complete changelog including bug fixes and deprecations
- [conda Enhancement Proposals (CEPs)](https://github.com/conda/ceps) — design documents driving these features
:::
