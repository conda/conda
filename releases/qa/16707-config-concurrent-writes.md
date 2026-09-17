### Title

Reject stale configuration writes.

### Why

A concurrent replacement must not silently discard an earlier writer's changes.

### Platforms

- [x] Windows
- [x] macOS
- [x] Linux

### Prerequisites

Use Python from an environment containing the conda build under test.

### Steps

1. In a Python session, create a temporary configuration and prepare an edit:

   ```python
   from pathlib import Path
   from tempfile import TemporaryDirectory
   from conda.cli.condarc import ConfigurationFile

   directory = TemporaryDirectory()
   path = Path(directory.name) / ".condarc"
   path.write_text("changeps1: true\n")
   config = ConfigurationFile(path)
   config.set_key("changeps1", False)
   ```

2. Replace the source with identical contents, then attempt the pending write:

   ```python
   replacement = path.with_name("replacement")
   replacement.write_bytes(path.read_bytes())
   replacement.replace(path)
   config.write()
   ```

3. Confirm `CondaError` reports that the file changed after reading and the file
   still contains `changeps1: true`.
4. Call `config.read()`, set `changeps1` to `False`, and write. Set it back to
   `True` and write again. Both writes must succeed.
5. Repeat with `CONDA_NO_LOCK=true`. Configuration locking must remain enabled.
6. Confirm no staged `.tmp` files remain, then call `directory.cleanup()`.

### Pass criteria

A stale write preserves the replacement. Reading again allows repeated edits.

### Out of scope / notes

A persistent `.condarc.lock` file is expected. Automated tests cover cooperating
threads and processes. Editors ignoring this lock can still race replacement.
