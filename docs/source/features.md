# Latest Features

Highlights of the most recent improvements to `conda`, organized by release.
For the full list of changes, see the {doc}`release-notes`.

---

## 26.3 — March 2026

:::{card} conda-lockfiles now ready for early beta testing

[conda-lockfiles](https://github.com/conda-incubator/conda-lockfiles) is an incubator project ready for beta testers and early adopters. This plugin adds support for generating lock files via `conda export` and recreating them via `conda create`.

Starting with an existing environment you can create a lock file by using the `conda export`:

```bash
# Create environment from lockfile
conda export --name my-env --format conda-lock-v1 > conda.lock
```

Once you've generated the lockfile, you can then recreate the environment using `conda create`:

```bash
conda create --file conda.lock --name my-env-new
```

This is especially useful for scenarios where you are looking to boost speed for CI environments or want to share environments across multiple computers.

To get started using it, install this plugin into your base environment:

```bash
conda install --name base conda-forge::conda-lockfiles
```

Please see the [conda-lockfiles documentation](https://conda-incubator.github.io/conda-lockfiles/) for more information

+++
{bdg-light}`experimental` <span style="float:right">{fab}`github` [conda-lockfiles](https://github.com/conda-incubator/conda-lockfiles)</span>

:::

:::{card} `conda create --file <env>` now supports all file types

The `conda create` command now supports environment.yaml files as well as requirements.txt and explicit environment exports, and detects name and prefix automatically when --name / --prefix are omitted.

The following invocations are now possible:

```bash
conda create --file environment.yaml
conda create --file requirements.txt
```

+++
{bdg-primary}`user experience` <span style="float:right">{fab}`github` [#15770](https://github.com/conda/conda/pull/15770)</span>
:::


---

:::{seealso}
- {doc}`release-notes` — complete changelog including bug fixes and deprecations
- [conda Enhancement Proposals (CEPs)](https://github.com/conda/ceps) — design documents driving these features
:::
