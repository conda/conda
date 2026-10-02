# Releasing

The `conda` release process is documented in `RELEASE.md` at the root of the repository on GitHub.
It covers the full end-to-end process: opening a release issue, running rever, publishing
the release, and bumping feedstocks.

:::{seealso}
[Release process (RELEASE.md)](https://github.com/conda/conda/blob/main/RELEASE.md)
:::

Stable releases also trigger the `Conda binaries` workflow, which builds executable distributions and publishes their coordinated update packages. See the [binary release tooling](https://github.com/conda/conda/blob/main/runtime/README.md) for its publication sequence, credentials, and rehearsal procedure.
