# Conda binaries

The `Conda binaries` workflow builds ready-to-use conda executables when a stable `X.Y.Z` GitHub release is published. It ports the executable distribution and updater from [conda-runtime](https://github.com/jezdez/conda-runtime). It is separate from [conda-standalone](https://github.com/conda/conda-standalone).

Each executable contains Python, conda built from the release tag, conda's packaged plugins, and `conda-runtime-updater`. The released conda-ship 0.9.2 builder and templates provide the executable and embedded bootstrap. Conda-ship is not installed in the managed prefix.

| Platform | Executable |
| --- | --- |
| Linux x86-64 with glibc | `conda-x86_64-unknown-linux-gnu` |
| Linux AArch64 with glibc | `conda-aarch64-unknown-linux-gnu` |
| macOS Intel | `conda-x86_64-apple-darwin` |
| macOS Apple silicon | `conda-aarch64-apple-darwin` |
| Windows x86-64 | `conda-x86_64-pc-windows-msvc.exe` |

## Installation and updates

After the binary workflow completes, download `install.sh` or `install.ps1` from that release. The installers verify the executable against `SHA256SUMS`, install it under `~/.local/bin` by default, and refuse to overwrite an existing file. They record direct ownership so `conda self update` can update both conda and the executable.

The first invocation extracts the embedded environment without network access. Its frozen base prefix lives in the platform's user-data directory under `conda/binary`. Set `CONDA_SHIP_PREFIX` persistently to choose another prefix. User environments and packages use `~/.conda/envs` and `~/.conda/pkgs`.

The managed prefix uses `https://conda.anaconda.org/conda/label/runtime` followed by conda-forge with strict channel priority. The updater stages the matching `conda-runtime` package and holds its lock until the conda transaction and executable replacement finish. It preserves JSON output, quiet mode, dry runs, declined updates, and interruption recovery. Windows uses a deferred replacement worker. Externally owned installations retain their recorded update instructions.

These binaries use a separate managed-prefix directory from the original conda-runtime distribution. Existing installations continue to use their recorded publisher and are not automatically migrated.

## Release sequence

1. Build conda from the release tag with the existing recipe and build the updater once as a noarch package. Both use the release version. Canary builds keep their existing version scheme.
2. Attest and attach those six packages to the existing GitHub release. Their permanent URLs and SHA256 digests become explicit dependencies in generated Pixi manifests, avoiding a feedstock publication dependency and preserving download URLs for recovery.
3. Lock each native environment, build with released conda-ship, exercise offline bootstrap, and verify macOS ad-hoc signatures. Preserve all generated manifests and locks in `conda-build-records.zip` alongside the release assets.
4. Package the finalized executable bytes into native update packages, verify their payloads, render installers, validate the complete distribution, and calculate checksums.
5. Exercise installers and two-generation updates on Linux, macOS, and Windows. The private-channel proof uses conda 26.5.2 as its baseline and covers dry runs, JSON, quiet mode, declined approval, inner failure, successful and repeated updates, external replacement, and Linux interruption recovery.
6. Attest and attach executables, SBOMs, installers, and checksums. Publish conda and updater packages to `conda/label/runtime`, verify visibility, then publish native update packages last.

The workflow preserves release notes and source archives. Reruns accept an existing file only when its size and SHA256 match. They never replace release assets or conda packages. Changed published bytes require a new conda release version.

This follows conda's existing `release: published` process, which allows adding assets after publication. Enabling immutable GitHub releases requires moving all source and binary uploads before publication in both release workflows.

CycloneDX SBOMs cover the resolved conda package graph, excluding the outer executable's Rust dependencies, host system, and code outside package records. GitHub attestations record provenance. macOS signatures are ad-hoc, without Developer ID notarization. Windows binaries are not Authenticode-signed.

## Repository setup

Before merging, configure the `runtime` GitHub environment with `ANACONDA_ORG_CONDA_TOKEN`. It must allow uploads of `conda`, `conda-runtime-updater`, and `conda-runtime` under the `conda` owner with the `runtime` label. Configure any required environment reviewers. The GitHub token needs release-asset and attestation permissions.

This draft proposes `conda/label/runtime` as the official update channel. Its package ownership and credentials must be configured before publication. The dedicated label avoids old packages in the historical conda channel taking precedence over current conda-forge dependencies. It does not depend on the original distribution's personal channel.

## Development and rehearsal

The updater remains a separate Python distribution in `runtime/updater`, installed only in these binaries. Its development version is `0.1.0`. The recipe sets wheel and package versions from `CONDA_RUNTIME_VERSION` inside a copied build source.

Run focused tests from the repository root:

```sh
pixi run --manifest-path runtime/updater/pyproject.toml --locked \
  python -m pytest -c runtime/updater/pyproject.toml runtime/updater/tests runtime/tests
```

Regenerate `runtime/updater/pixi.lock` whenever its workspace settings or dependencies change.

Relevant pull requests and manual `Conda binaries` runs rehearse the build and proofs without publishing assets, packages, or attestations. They use local package URLs and default to the next patch version after the latest stable tag. A manual run can override that version. Only a stable release event in `conda/conda` publishes, and prereleases are skipped.
