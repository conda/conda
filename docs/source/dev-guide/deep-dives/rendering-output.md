(deep_dive_rendering_output)=
# Rendering output

This guide describes how conda displays output to users: which mechanism to use for which kind of
output, and how to use it. There are four distinct channels, each with a different purpose:

| What you want to show | Use | Goes to |
| --- | --- | --- |
| Command results, progress, prompts (the "product" of the command) | The **reporter backend** via {mod}`conda.reporters` | stdout |
| Diagnostics, informational notes and warnings for developers and for troubleshooting | **Loggers** via {func}`logging.getLogger` | stderr (when handlers are configured) |
| Errors that end the command | **Exceptions** (subclasses of {class}`~conda.CondaError`) | stderr, via the {ref}`exception handler <rendering_output_errors>` |
| Free-form user-facing text that predates the reporter backend | Legacy helpers in {mod}`conda.gateways.streams` | stdout/stderr (see {ref}`rendering_output_legacy`) |

```{admonition} Direction of travel
:class: note

The reporter backend is intended to be the **single output system** for the conda CLI. This is
tracked in [conda/conda#15477](https://github.com/conda/conda/issues/15477). The page you are
reading documents the current state and the conventions that new code should follow. Parts of the
legacy channel (the `conda.stdout`, `conda.stderr`, `conda.stdoutlog`, `conda.stderrlog` and
`conda.stdout.verbose` loggers) are deprecated (removal in 27.3); see {ref}`rendering_output_legacy`.
```

## The reporter backend

A *reporter backend* is a plugin (see {doc}`/dev-guide/plugins/reporter_backends`) that controls how
conda renders output. conda ships two:

* `console`: the default, human-readable output ({mod}`conda.plugins.reporter_backends.console`).
* `json`: machine-readable output, used whenever `--json` is passed
  ({mod}`conda.plugins.reporter_backends.json`).

Every backend provides a *renderer* class derived from
{class}`~conda.plugins.types.ReporterRendererBase`. The renderer knows how to turn data into
strings and how to create the interactive elements below:

| Renderer method | Purpose |
| --- | --- |
| `render(data)` | Render arbitrary data. The default is `str(data)`; `console` appends a trailing newline and `json` serializes to JSON. |
| `detail_view(data)` | Render a `dict` as a table of aligned `key : value` rows. |
| `envs_list(data)` | Render a list of environments. |
| `progress_bar(description)` | Create a {class}`~conda.plugins.types.ProgressBarBase`. |
| `spinner(message, fail_message)` | Create a {class}`~conda.plugins.types.SpinnerBase`. |
| `prompt(message, choices, default)` | Ask a question (used for yes/no confirmation). |

### Backend selection

Code that renders output should **never** import a backend or check which one is active. All
selection happens in {mod}`conda.reporters`, which looks up {attr}`context.console
<conda.base.context.Context.console>` and asks the plugin manager for the matching backend:

* `context.json` is `True` (`--json`): the `json` backend is always used.
* Otherwise the `console` setting (`--console` or `console:` in `.condarc`) is used. It defaults to `console`.

The renderer lookup is cached. If you change the setting at runtime (normally only in tests), call
{func}`conda.base.context.reset_context`, which also clears this cache.

### API reference

Callers interact with the backend through the functions in {mod}`conda.reporters`:

| Function | Purpose |
| --- | --- |
| {func}`~conda.reporters.render` | Write rendered data to stdout. |
| {func}`~conda.reporters.get_spinner` | Return a spinner context manager for long-running work. |
| {func}`~conda.reporters.get_progress_bar` | Return a progress bar object. |
| {func}`~conda.reporters.get_progress_bar_context_manager` | Return the context manager that wraps progress bar usage (a null context by default). |
| {func}`~conda.reporters.confirm_yn` | Ask a yes/no question. Honors `--dry-run` and `--yes`. |

### Rendering data

{func}`~conda.reporters.render` takes the data and an optional `style`. Without a `style` the
renderer's generic `render` method is used. With a `style`, the renderer method of that name is
used (`"detail_view"`, `"envs_list"`, ...). Any extra keyword arguments are passed on to the renderer
method. An unknown style raises {class}`AttributeError`.

```python
from conda.reporters import render

# Generic rendering. In console mode this prints "hello\n"; in JSON mode, '"hello"'.
render("hello")

# A table of key/value pairs.
render({"name": "myenv", "frozen": False}, style="detail_view")
#  name : myenv
# frozen : False

# Style-specific keyword arguments are forwarded to the renderer.
render(prefixes, style="envs_list", show_size=True)
```

Because the data is handed to the backend unchanged, **pass structured data, not pre-formatted
text**, whenever the output has any structure. This is what lets the `json` backend emit something
useful and lets other backends restyle the output.

`conda info` is a good example of this pattern. Each component produces its data and names the
renderer style it needs, and the shared loop in {class}`conda.cli.main_info.InfoRenderer` renders
it (simplified):

```python
from conda.reporters import render

style_by_component = {"base": None, "detail": "detail_view", "envs": "envs_list"}

for component in components:
    data = get_component_data(component)  # str, or dict when context.json is set
    if data:
        render(data, style=style_by_component[component])
```

For commands that only need to emit a JSON document, {func}`conda.cli.common.stdout_json` is a thin
wrapper around `render(data)` that also swallows broken pipes. Its companion
{func}`conda.cli.common.stdout_json_success` builds the conventional `{"success": true, ...}`
payload. Use them for the `--json` branch of a command:

```python
from conda.base.context import context
from conda.cli.common import stdout_json

if context.json:
    stdout_json({"env_vars": env_vars})
else:
    for key, value in env_vars.items():
        print(f"{key} = {value}")  # see "Plain text" below
```

```{note}
Writing a command's result in both a JSON and a non-JSON form is common today. Where a renderer
style exists for your data (as with `detail_view` and `envs_list`), prefer a single
`render(data, style=...)` call and let the backend decide.
```

### Spinners

A spinner tells the user that a long-running step is in progress. Use {func}`~conda.reporters.get_spinner`
as a context manager. If the body raises, `fail_message` is printed instead of `done`.

```python
from conda.reporters import get_spinner

with get_spinner("Solving environment", fail_message="failed\n"):
    solution = solver.solve_final_state()
```

This is how the solver and transaction code report progress, for example in `conda.core.link`:

```python
with get_spinner("Preparing transaction"):
    ...
with get_spinner("Verifying transaction"):
    ...
with get_spinner("Executing transaction"):
    ...
```

The `console` backend automatically degrades to a static `message: ...working... done` line when
output is not a TTY, `TERM=dumb`, or `--quiet` is set. The `json` backend emits nothing.
**Callers do not need to check any of these conditions.**

### Progress bars

Progress bars report fractional progress, for example while downloading packages.
{func}`~conda.reporters.get_progress_bar` returns an object you update with a fraction between `0`
and `1`:

```python
from conda.reporters import get_progress_bar

pbar = get_progress_bar("numpy-2.0.0")
try:
    for fraction in download():
        pbar.update_to(fraction)
    pbar.finish()
finally:
    pbar.close()
```

When several progress bars are active at once (for example during parallel downloads), wrap the work
in {func}`~conda.reporters.get_progress_bar_context_manager` so a backend can coordinate them. The
default is a null context, so this is always safe to use:

```python
from conda.reporters import get_progress_bar, get_progress_bar_context_manager

with get_progress_bar_context_manager():
    pbar = get_progress_bar("Downloading")
    ...
```

The `console` backend returns a `tqdm` bar, or a silent bar under the same conditions as spinners.
The `json` backend emits newline/NUL-delimited JSON progress records (`{"fetch": ..., "progress": ...}`),
which is what `conda install --json` consumers parse.

### Prompts

Use {func}`~conda.reporters.confirm_yn` to ask the user for confirmation. It handles the cross-cutting
cases for you:

* If `--dry-run` is set, it raises {class}`~conda.exceptions.DryRunExit`.
* If `--yes` is set, it returns `True` without prompting.
* If the user answers "no" or presses Ctrl-C, it raises {class}`~conda.exceptions.CondaSystemExit`
  (a "clean" exit with return code `0`).
* Otherwise it returns `True`.

```python
from conda.reporters import confirm_yn

confirm_yn()  # "Proceed ([y]/n)? "
confirm_yn("Remove these files", default="no")
```

Because "no" is signalled by an exception, code after the call can assume the user agreed.

## Loggers

{ref}`deep_dive_logging` covers creating a logger with `getLogger(__name__)`, choosing a level,
and leaving handlers, levels, and propagation to the caller.

(rendering_output_logger_or_reporter)=
### Choosing between a logger and the reporter

A useful rule of thumb: **if the text is the answer to what the user asked, render it; if it is
commentary about how conda got there, log it.**

| Situation | Use                                                |
| --- |----------------------------------------------------|
| `conda list`, `conda info`, `conda config --show` output | Reporter (`render`)                                |
| "Solving environment" status | Reporter (`get_spinner`)                           |
| "Proceed ([y]/n)?" | Reporter (`confirm_yn`)                            |
| Download progress | Reporter (`get_progress_bar`)                      |
| "Skipping unreadable `environments.txt`" | `log.warning`                                      |
| "Found python 3.12 in the transaction" | `log.debug`                                        |
| A package failed to link | Raise an exception (e.g. `CondaError` or subclass) |

Logging output goes to stderr and the reporter writes to stdout. This keeps `conda list --json |
jq` and similar pipelines clean even when warnings are emitted. Output is rendered as soon as
either the `render` or `logging` functions are called. Raising a `CondaError` renders the error message
as well as immediately halting program execution.

(rendering_output_errors)=
## Errors

Do not print error messages. Raise an exception, and let the exception handler render it.

```python
from conda.exceptions import CondaValueError

if not path.exists():
    raise CondaValueError(f"could not find environment file: {path}")
```

When an exception propagates out of a command, {class}`conda.exception_handler.ExceptionHandler`
decides what to show:

* {class}`~conda.CondaError` subclasses are *expected* errors. Their message is
  formatted by {func}`conda.exceptions.print_conda_exception` and written to stderr. With `--json`,
  the error is serialized to a JSON object instead. Subclasses marked `reportable` additionally
  produce the full error report and may offer to upload it.
* Other exceptions are *unexpected*. The handler builds an error report (traceback, `conda info`,
  environment variables) and prints it to stderr, or emits it as JSON when `--json` is set.
* {class}`KeyboardInterrupt`, {class}`MemoryError` and out-of-disk-space errors are translated to
  the appropriate conda error first.

Using exceptions for errors provides consistent formatting, correct exit codes
(`CondaError.return_code`), `--json` support, and the ability for
{doc}`exception observer </dev-guide/plugins/exception_observers>` and
{doc}`error hint </dev-guide/plugins/error_hints>` plugins to react. A `print` or a `log.error`
bypasses all of these.

Use a logger's `warning` level, not an exception, only when the command can still succeed.

(rendering_output_legacy)=
## Legacy output channels

Older code writes user-facing text without going through the reporter backend. You will see these
in the code base and should not copy them into new code.

### Custom loggers

The loggers `conda.stdout`, `conda.stderr`, `conda.stdoutlog`, `conda.stderrlog` and
`conda.stdout.verbose` wrote straight to stdout/stderr and were configured by
`conda.gateways.logging.initialize_std_loggers`. That function and the loggers are **pending
`conda.gateways.logging.initialize_std_loggers`. That function and the loggers are
**deprecated** (removal in conda 27.3) and are no longer configured during normal CLI startup. Their meaning was also
ambiguous (what is a `warning` on a logger named `stdout`?).

### `conda.gateways.streams`

The module {mod}`conda.gateways.streams` contains helpers that replaced the custom loggers as a
transitional step. They print to the corresponding stream and redact channel tokens:

| Helper | Behavior |
| --- | --- |
| `stdout(text)` / `stderr(text)` | Always print. |
| `stdoutlog(text)` / `stderrlog(text)` | Print unless `context.json` is set. |

Typical existing uses:

```python
# conda/resolve.py
if not context.json:
    from .gateways.streams import stdoutlog

    stdoutlog("\nWarning: ... possible package resolutions ...")

# conda/instructions.py
from .gateways.streams import stdoutlog

stdoutlog(str(arg))
```

These calls bypass the selected reporter backend, so a non-default backend cannot restyle them and
they duplicate the `--json` checks that `render` already performs. They remain only until usages are
migrated.

### Migration guidance

When touching code that uses one of these channels:

| Existing code | Replace with |
| --- | --- |
| `stdoutlog(...)` conveying a command result or status | `render(...)`, `get_spinner(...)`, or `get_progress_bar(...)` |
| `stdoutlog(...)` conveying a caveat for the user | `log.warning(...)` |
| `stderrlog(...)` or `getLogger("conda.stderr*")` reporting a problem | `log.warning(...)`, or raise an exception if the command cannot continue |
| `print(...)` in a library function | `render(...)`, or `log.debug(...)` for diagnostics |
| `getLogger("conda.stdout").info(...)` | `render(...)` |

Bare `print` calls are still present in some commands. Treat them the same way: if the text is
output the user asked for, route it through the reporter; if it is diagnostic, use a logger.

## Writing tests

Use the `capsys` fixture to assert on what a command renders to stdout and stderr, and
`caplog` for log records. To exercise a specific backend, pass `--json` or set `console` through
the usual context fixtures rather than patching {mod}`conda.reporters`.

```python
import json

from conda.testing.fixtures import CondaCLIFixture


def test_info_json(conda_cli: CondaCLIFixture):
    out, err, rc = conda_cli("info", "--json")
    assert rc == 0, err
    assert "conda_version" in json.loads(out)


def test_warning_is_logged(caplog):
    caplog.set_level("WARNING", logger="conda.core.envs_manager")
    ...
```

## Summary

* Render results, progress and prompts with {mod}`conda.reporters`. Pass structured data.
* Emit diagnostics with `getLogger(__name__)`. Never configure handlers in library code.
* Report failures by raising a {class}`~conda.CondaError`; the exception handler renders it.
* Do not add new uses of the `conda.stdout*`/`conda.stderr*` loggers, or of
  `conda.gateways.streams.stdoutlog`/`stderrlog`.
