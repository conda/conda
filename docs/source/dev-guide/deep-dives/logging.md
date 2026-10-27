(deep_dive_logging)=
# Logging

Loggers record diagnostics. That includes notes that help a developer or a user troubleshoot a
problem, and warnings about conditions that are surprising but do not stop the command. Command
results go through the reporter.

The conventions are:

* Every module creates one logger named after itself, at import time:

  ```python
  from logging import getLogger

  log = getLogger(__name__)
  ```

* Library code emits records and does not configure handlers, levels, or propagation. When conda
  runs as a CLI, `conda.cli.main.init_loggers` attaches the handlers and sets the level from the
  verbosity flags. When another program imports conda, that program configures logging.
* Use lazy `%`-style arguments rather than f-strings so formatting only happens if the record is
  emitted.
* Pass `exc_info=True` to `log.debug` to record a traceback without showing it to the user.

| Level | Use for | Visible when |
| --- | --- | --- |
| `debug` | Internal state, decisions taken, caught-and-ignored exceptions | `-vvv` / `--debug` |
| `info` | Notable steps in normal operation | `-vv` |
| `warning` | Something is wrong or degraded, but conda can continue | Always (default level) |

The `-v` flags map to levels in {attr}`context.log_level <conda.base.context.Context.log_level>`:

| Flags | `context.verbosity` | Logging level |
| --- | --- | --- |
| *(none)* | 0 | `WARNING` |
| `-v` | 1 | `WARNING` (and more detailed command output) |
| `-vv` | 2 | `INFO` |
| `-vvv` / `--debug` | 3 | `DEBUG` |
| `-vvvv` / `--trace` | 4 | `TRACE` |

Examples from the code:

```python
# conda/core/link.py: internal diagnostics
log.debug("no python version found in prefix")

# conda/core/envs_manager.py: a recoverable problem, reported as a warning
log.warning(
    "Unable to register environment. Could not create %s. Reason: %s",
    user_environments_txt_directory,
    exc,
)

# Recording a swallowed exception for later debugging
try:
    ...
except OSError as e:
    log.debug(repr(e), exc_info=True)
```

A filter on the CLI handlers redacts channel tokens in URLs (`/t/<token>/`). Log those URLs as
they are. Do not log other secrets.

See {ref}`rendering_output_logger_or_reporter` for whether to log a message or render it.
