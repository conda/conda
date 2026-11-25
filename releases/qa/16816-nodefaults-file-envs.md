### Title
`nodefaults` in file-based environments

### Why
`conda env create` and `conda create -f` were appending `.condarc` channels and requesting `nodefaults` as a channel URL. This broke air-gapped and private-mirror setups and violated CEP-24.

### Platforms
- [ ] Windows
- [ ] macOS
- [ ] Linux

### Prerequisites
- Network access to conda-forge, or a reachable mirror configured as the file channel.
- No local channel or package build required.
- Examples use POSIX environment-variable syntax. On Windows, set `CONDA_CHANNELS` with `set` or `$env:` before running the command.

### Steps
1. Create `environment.yml`:
   ```yaml
   name: nodefaults-qa
   channels:
     - conda-forge
     - nodefaults
   dependencies:
     - zlib
   ```
2. Run with a deliberately nonexistent configured channel:
   ```console
   CONDA_CHANNELS=conda-forge-nonexistent-qa conda create -f environment.yml --dry-run
   ```
3. Repeat with `conda env create -f environment.yml --dry-run`.
4. Create `environment-nf-only.yml`:
   ```yaml
   name: nodefaults-qa-only
   channels:
     - nodefaults
   dependencies:
     - zlib
   ```
5. Run with a reachable configured channel:
   ```console
   CONDA_CHANNELS=conda-forge conda create -f environment-nf-only.yml --dry-run
   ```

### Pass criteria
- Steps 2 and 3 succeed from conda-forge, with no error about `conda-forge-nonexistent-qa`.
- Step 5 succeeds using the configured `conda-forge` channel.
- No command requests `<channel_alias>/nodefaults`; optionally confirm with `-vv`.

### Notes
- A deliberately nonexistent configured channel is better than a real extra channel: if the file’s `nodefaults` is ignored, the solve fails fast on the bogus channel instead of succeeding silently.
- For air-gapped/private-mirror testing, replace `conda-forge` in the file with the reachable mirror and keep the bogus configured channel. Local channel setup is only needed for that variant.
- `.condarc`/`-c` sentinel behavior and the legacy `conda env update` path are out of scope for this patch.
