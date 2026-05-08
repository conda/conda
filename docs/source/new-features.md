# New features to try

Recent additions to `conda` worth your attention, including features still in beta that we'd love your feedback on. For the full list of changes across releases, see the {doc}`release-notes`.

**Stage legend**
{bdg-success}`Stable` — on by default, recommended for all users.
{bdg-warning}`Beta` — opt in to test, not recommended for production, we want your feedback.

---
## **Install PyPI packages with `conda install`**
::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-beta

{bdg-light}`Available in conda 26.5` &nbsp; {bdg-warning}`Beta`

New `conda-pypi` plugin lets you to install PyPI packages natively with `conda install`. Conda resolves across both conda channels and PyPI in a single solve, and PyPI wheel packages behave like any other conda package once installed: they show up in `conda list`, get captured in `conda export`, and uninstall cleanly with `conda remove`.

This replaces the common workaround of running `pip install` inside a conda environment, which can leave you with packages conda doesn't know about, environments that are hard to reproduce, and conflicts that surface only later and hard to debug.

### How to opt in

1. Make sure you're on conda 26.5 or later. To update:
    ```bash
    conda install -n base `conda>=26.5.0`
    ```
2. Enable the [Rattler solver](#faster-solves-with-rattler-solver) and add the `conda-pypi` channel:
    ```bash
    conda config --set solver rattler &&\
    conda config --append channels conda-pypi
    ```
### Basic usage
Before, you'd install conda packages, then pip-install packages from PyPI:
```bash
conda install pandas scikit-learn
pip install some-pypi-package
```

With conda-pypi enabled, you only need one command:
```bash
conda install pandas scikit-learn some-pypi-package
```
### What's next
We want to hear what works, what doesn't, and what should come next. Open an issue or join the discussion below.

[Full documentation](https://conda.github.io/conda-pypi) · [Open a GitHub issue](https://github.com/conda/conda/issues) · [Join the discussion in Zulip](https://conda.zulipchat.com/)
::::

## **Faster solves with Rattler solver**

::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-beta

{bdg-light}`Available in conda 26.5` &nbsp; {bdg-warning}`Beta`

Rattler is a Rust-based solver developed within the conda ecosystem by the team at Prefix.dev. It's on track to become conda's next default solver, and trying it now helps shape how the transition goes.

Environments solve meaningfully faster with Rattler, especially large or complex ones. It's the same solver that powers pixi, where it's earned a reputation for handling tough specs quickly. Your existing environments and workflows keep working. Rattler is a drop-in replacement for the current solver, not a new way of doing things.

### How to opt in
Update conda and switch your default solver to Rattler:

    ```bash
    conda install -n base 'conda>=26.5'
    conda config --set solver rattler
    ```
To switch back at any time:
```bash
conda config --remove-key solver
```
### What's next
Rattler is planned to become the default solver in a conda 27.x release. Trying it now and reporting issues helps us decide when it's ready and shapes how the transition will work for the wider community

[Full documentation](https://github.com/conda-incubator/conda-rattler-solver) · [Open a GitHub issue](https://github.com/conda/conda/issues) · [Join the discussion in Zulip](https://conda.zulipchat.com/)
::::

## **Native multi-platform lockfile support**

::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-stable

{bdg-light}`Available in conda 26.5` &nbsp; {bdg-success}`Stable`

Available to everyone running conda 26.5. No opt-in required.

`conda export`, `conda create`, and `conda install` now support lockfiles as a first-class artifact. A lockfile records the exact packages, versions, builds, and channels in an environment, and conda can read it back to recreate that environment exactly. The multi-platform format records this for several platforms in a single file, so the same lockfile recreates the environment on Linux, macOS, and Windows.

When creating or installing from a lockfile, **conda skips solving entirely** and goes straight to downloading and installing the pinned packages. For large environments, or environments rebuilt repeatedly in CI, this is the difference between minutes of solving on every run and a fast, deterministic install.

Conda supports the `conda-lock.yaml` and `pixi.lock` formats natively. No separate plugin or third-party tool is required.

### Basic usage

**Make sure you're on conda 26.5 or later** to use this feature:

Export an environment to a lockfile:

```bash
conda export -n my-env --file conda-lock.yaml
```
Recreate the environment on another machine:

```bash
conda create -n my-env --file conda-lock.yaml
```
By default, the lockfile captures only the platform you exported from. To capture multiple platforms in one file, pass `--platform` once per target:

```bash
conda export -n my-env --file conda-lock.yaml \
  --platform linux-64 \
  --platform osx-arm64 \
  --platform win-64
```
### A few things to keep in mind

 - **Reproducibility depends on the channel.** A lockfile pins exact packages, but those packages need to still be available when you recreate. If a package is removed or yanked later, the recreate will fail.
 - **`pip`-installed packages aren't captured by default.** `conda export` to a lockfile captures conda packages only. If you need PyPI packages reproducibly captured, see [Install PyPI packages with conda](#install-pypi-packages-with-conda-install) above. That path lets PyPI packages flow through conda and show up in exports.

[Full documentation](https://conda-incubator.github.io/conda-lockfiles/getting-started/) · [Open a GitHub issue](https://github.com/conda/conda/issues) · [Join the discussion in Zulip](https://conda.zulipchat.com/)
::::

