# New features to try
 
Recent additions to `conda` worth your attention, including features still in beta that we'd love your feedback on. For the full list of changes across releases, see the {doc}`release-notes`.

**Stage legend**
- {bdg-success}`Stable` — on by default, recommended for all users.
- {bdg-warning}`Beta` — opt in to test, not recommended for production, we want your feedback.

---
## Install PyPI packages in conda
::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-beta
 
{bdg-light}`Available since conda 26.5` &nbsp; {bdg-warning}`Beta`

 
Mixing conda and pip is common, and under certain conditions it causes difficult-to-debug problems: environments that worked yesterday but don't today, partial reproducibility, packages that conda can't see because pip installed them behind its back. Read: [why mixing pip and conda is risky](#).
 
The `conda-pypi` plugin is a community effort to make the two packaging ecosystems work together more safely. With it enabled, conda resolves across both conda channels and PyPI in a single solve. PyPI packages install through conda directly. They appear in `conda list`, export through `conda env export`, and uninstall with `conda remove`, the same as any conda package. No more separate `pip install` step, and no more packages hiding from conda.
**How to opt in**
 
1. Make sure you're on conda 26.5 or later. To update:
    ```bash
    conda update -n base conda
    ```
 
2. Enable the Rattler solver and add the `conda-pypi` channel:
    ```bash
    conda config --set solver rattler
    conda config --append channels conda-pypi
    ```
 
**Basic usage**
 
Before, you'd install conda packages first, then pip-install the rest:
 
```bash
conda install pandas scikit-learn
pip install some-pypi-package
```
 
With the plugin enabled, one command resolves both:
 
```bash
conda install pandas scikit-learn some-pypi-package
```
**What's next**
This is the first step in a longer effort to give conda users a more reliable path to PyPI packages without switching tools or breaking environments. We'll be guided by what we hear from beta users about where this works well, where it falls short, and what the next milestone should be.
 
[Full documentation](https://conda.github.io/conda-pypi/features/#wheel-channels) · [Open a GitHub issue](https://github.com/conda/conda/issues) · [Join the discussion in Zulip](https://conda.zulipchat.com/)
::::
 
## Rust-based Rattler solver for conda
 
::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-beta
 
{bdg-light}`Available since conda 26.5` &nbsp; {bdg-warning}`Beta`

 
 The [last major solver update](https://conda.org/blog/2023-11-06-conda-23-10-0-release/) brought a dramatic speedup. Today, we're inviting you to try the next one.
 
`conda-rattler-solver` is a Rust-based solver developed within the conda ecosystem by the team at Prefix.dev. It's the same solver that powers pixi. For many environments you'll see meaningfully faster solves, especially on large or complex specs. Adopting Rattler is also part of a broader direction for the conda ecosystem: moving core components to more modern, performant technologies like Rust.
 
**How to opt in**
 
Update conda and switch your default solver to Rattler:

    ```bash
    conda install -n base 'conda>=26.5'
    conda config --set solver rattler
    ```
That's it. Your existing environments and workflows keep working. To switch back at any time:
 
```bash
conda config --remove-key solver
```
**What's next**
Rattler is planned to become the default solver in an conda 27.x release. Trying it now and reporting issues helps us decide when it's ready, and shapes how the transition will work for the wider community.
 
[Full documentation](https://github.com/conda-incubator/conda-rattler-solver) · [Open a GitHub issue](https://github.com/conda/conda/issues) · [Join the discussion in Zulip](https://conda.zulipchat.com/)
::::
 
## Native multi-platform lockfile support
 
::::{card}
:class-card: sd-rounded-3 conda-feature-card conda-feature-stable
 
{bdg-light}`Available since conda 26.5` &nbsp; {bdg-success}`Stable`
 
Available to everyone running conda 26.5. No opt-in required.
 
`conda export` and `conda create` now support lockfiles that capture an environment for one or more platforms in a single file. Lockfile support is built into conda. No separate plugin or third-party tool is required.
 
A lockfile records the exact packages, versions, builds, and channels needed to reproduce an environment. The multi-platform format records this for several platforms at once, so a single file can recreate the same environment on Linux, macOS, and Windows. Hand it to a teammate on a different OS, ship it with your project, or check it into CI, and you'll get the same environment back.

**Make sure you're on conda 26.5 or later** to use this feature:
 
```bash
conda update -n base conda
``` 
**Basic usage**
 
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
  --platform linux-64 --platform osx-arm64 --platform win-64
```
**A few things to keep in mind**
 
 - A lockfile pins exact packages, but reproducibility depends on those packages still being available in the channel you used. If a package is later removed or yanked, recreating from the lockfile will fail. For long-term archival, mirror the channel or pin to a channel you control.
 - `conda export` to a lockfile captures conda packages only. Packages installed into the environment via `pip` or other third-party tools won't appear in the lockfile. If you need pip packages reproducibly captured, see [Install from PyPI with conda](#install-from-pypi-with-conda) above, which lets pip packages flow through conda and be captured in exports.

[Full documentation](https://conda-incubator.github.io/conda-lockfiles/getting-started/) · [Open a GitHub issue](https://github.com/conda/conda/issues) · [Join the discussion in Zulip](https://conda.zulipchat.com/)
::::
 