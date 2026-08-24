# New features to try

This page contains recent additions to `conda` worth your attention, including features still in beta that we'd love your feedback on. For the full list of changes across releases, see the {doc}`release-notes`.

**Stage legend**<br />
{bdg-success}`Stable` — On by default, recommended for all users.

{bdg-warning}`Beta` — Opt in to test, not recommended for production. We want your feedback!

---
## Faster solves with Rattler solver

::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-beta

{bdg-light}`Available in conda 26.5 and later` &nbsp; {bdg-warning}`Beta`

The Rattler solver is on track to become conda's default solver in the near future. Try it now and report any issues to help shape the transition for the wider community.

To opt in, update conda and switch your default solver to Rattler:

```bash
conda install --name base 'conda>=26.7'
conda config --set solver rattler
```

To switch back at any time:

```bash
conda config --remove-key solver
```

[Full documentation](https://github.com/conda-incubator/conda-rattler-solver) · [Open a GitHub issue](https://github.com/conda/conda/issues) · [Join the discussion in Zulip](https://conda.zulipchat.com/)
::::

## Exclude packages newer than X time from solving and search
::::{card}
:class-card: sd-rounded-3 conda-feature-card

{bdg-light}`Available in conda 26.9 and later`

TBD
::::

## Install PyPI packages with `conda install`
::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-stable

{bdg-light}`Available in conda 26.5 and later` &nbsp; {bdg-success}`Stable`

The new `conda-pypi` plugin lets you install PyPI packages natively with `conda install`. Conda resolves across both conda channels and PyPI in a single solve, and PyPI wheel packages behave like any other conda package once installed: they show up in `conda list`, get captured in `conda export`, and uninstall cleanly with `conda remove`.

This replaces the common workaround of running `pip install` inside a conda environment, which can leave you with packages conda doesn't know about, environments that are hard to reproduce, and hard-to-debug conflicts that surface much later.

For more information on installing PyPI packages with `conda install`, see [Install PyPI packages with conda](user-guide/tasks/install-pypi-packages).
::::

## Native multi-platform lockfile support

::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-stable

{bdg-light}`Available in conda 26.5 and later` &nbsp; {bdg-success}`Stable`

Available to everyone running conda 26.5. No opt-in required.

`conda export`, `conda create`, and `conda install` now support lockfiles as a first-class artifact. A lockfile records the exact packages, versions, builds, and channels in an environment, and conda can use that lockfile to recreate that environment exactly. Lockfiles can also record the resolved packages for several platforms at once. With a multi-platform lockfile, the same file can recreate the environment on Linux, macOS, and Windows.

When creating or installing from a lockfile, **conda skips solving entirely** and goes straight to downloading and installing the pinned packages. For large environments, or environments rebuilt repeatedly in CI, this is the difference between minutes of solving on every run and a fast, deterministic install.

Conda supports the `conda-lock.yaml` and `pixi.lock` formats natively. No separate plugin or third-party tool is required.

For more information, see [Multi-platform lockfiles](user-guide/tasks/manage-environments#multi-platform-lockfiles)
::::
