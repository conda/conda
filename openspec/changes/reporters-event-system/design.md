# Design: Reporter Event System

## Architecture Overview

```
Calling code (solve.py, link.py, package_cache_data.py, ...)
    │
    │  uses module-level functions from conda/reporters.py:
    │    get_spinner("Solving...") → context manager
    │    get_progress_bar(desc)    → ProgressBarBase (deprecated shim)
    │    render(data, style=...)
    │
    ▼
conda/reporters.py — CondaReporter (global singleton)
    │  Responsibilities:
    │  - Ingests typed events from public API helpers
    │  - Owns dispatch table: event type → renderer method name
    │  - Manages cross-event state (fetch sessions, thread lock)
    │  - Selects active ReporterRendererBase via context.console
    │
    │  dispatches to
    ▼
conda/plugins/types.py — ReporterRendererBase (plugin contract)
    │  Responsibilities:
    │  - Pure rendering: "given this semantic thing, produce output"
    │  - No event routing, no lifecycle management, no TTY checks
    │  - Default no-op implementations for all render_* methods
    │  - prompt() retained as a synchronous query method
    │
    │  implemented by
    ▼
conda/plugins/reporter_backends/console.py — ConsoleReporterRenderer
conda/plugins/reporter_backends/json.py    — JSONReporterRenderer
conda-rich/conda_rich/hooks.py             — RichReporterRenderer (in-repo plugin)
    (third-party: additional plugins not in this repo)
```

---

## New Module: `conda/plugins/reporter_backends/events.py`

All typed event dataclasses. This is the canonical registry of every reportable
event in conda. All event classes are `frozen=True` dataclasses (immutable,
hashable, safe to pass across threads).

```python
# Output events
@dataclass(frozen=True)
class RenderDataEvent:
    data: Any
    style: str | None = None

@dataclass(frozen=True)
class DetailViewEvent:
    data: dict[str, str | int | bool]

@dataclass(frozen=True)
class EnvsListEvent:
    prefixes: tuple  # tuple of PathType | PrefixData
    show_size: bool = False

# Spinner events
@dataclass(frozen=True)
class SpinnerStartEvent:
    message: str
    fail_message: str = "failed\n"

@dataclass(frozen=True)
class SpinnerEndEvent:
    message: str
    success: bool

# Fetch/extract pipeline events
@dataclass(frozen=True)
class FetchSectionStartEvent:
    pass  # renderer can prepare its layout context

@dataclass(frozen=True)
class FetchTaskStartEvent:
    task_id: int          # caller provides: id(prec_or_spec)
    name: str
    version: str
    size: int | None

@dataclass(frozen=True)
class FetchTaskProgressEvent:
    task_id: int
    fraction: float       # 0.0–1.0

@dataclass(frozen=True)
class FetchTaskEndEvent:
    task_id: int
    success: bool

@dataclass(frozen=True)
class FetchSectionEndEvent:
    success: bool
```

A base `RenderEvent` type alias (or empty base class) allows type annotations
where any event is acceptable:

```python
RenderEvent = (
    RenderDataEvent | DetailViewEvent | EnvsListEvent |
    SpinnerStartEvent | SpinnerEndEvent |
    FetchSectionStartEvent | FetchTaskStartEvent |
    FetchTaskProgressEvent | FetchTaskEndEvent | FetchSectionEndEvent
)
```

---

## `CondaReporter` — The Singleton

Lives in `conda/reporters.py`. Replaces the `@cache` + `_get_render_func` pattern.

```python
class CondaReporter:
    _DISPATCH: dict[type, str] = {
        RenderDataEvent:        "render_data",
        DetailViewEvent:        "render_detail_view",
        EnvsListEvent:          "render_envs_list",
        SpinnerStartEvent:      "render_spinner_start",
        SpinnerEndEvent:        "render_spinner_end",
        FetchSectionStartEvent: "render_fetch_section_start",
        FetchTaskStartEvent:    "render_fetch_task_start",
        FetchTaskProgressEvent: "render_fetch_task_progress",
        FetchTaskEndEvent:      "render_fetch_task_end",
        FetchSectionEndEvent:   "render_fetch_section_end",
    }
    # Events that must be serialized across threads:
    _THREAD_SAFE_EVENTS: frozenset[type] = frozenset({
        FetchTaskStartEvent,
        FetchTaskProgressEvent,
        FetchTaskEndEvent,
    })

    def __init__(self, renderer: ReporterRendererBase) -> None:
        self._renderer = renderer
        self._lock = threading.Lock()

    def send(self, event: RenderEvent) -> None:
        method_name = self._DISPATCH.get(type(event))
        if method_name is None:
            logger.debug("unhandled event type: %s", type(event).__name__)
            return
        if type(event) in self._THREAD_SAFE_EVENTS:
            with self._lock:
                getattr(self._renderer, method_name)(event)
        else:
            getattr(self._renderer, method_name)(event)

    def prompt(self, message="Proceed", choices=("yes", "no"),
               default="yes") -> str:
        return self._renderer.prompt(message, choices, default)
```

Module-level singleton management:

```python
_reporter: CondaReporter | None = None

def get_reporter() -> CondaReporter:
    global _reporter
    if _reporter is None:
        backend = context.plugin_manager.get_reporter_backend(context.console)
        _reporter = CondaReporter(backend.renderer())
    return _reporter

def reset_reporter() -> None:
    global _reporter
    _reporter = None
```

`context.py` calls `reset_reporter()` instead of `_get_render_func.cache_clear()`.

---

## Updated `ReporterRendererBase` (plugin contract)

The renderer becomes a pure collection of `render_*` methods with default no-ops.
`prompt()` is retained as-is (synchronous query, not an event).
The old abstract methods (`progress_bar`, `spinner`, `progress_bar_context_manager`)
are marked deprecated.

```python
class ReporterRendererBase(ABC):

    # --- New render_* methods (no-op defaults, not abstract) ---

    def render_data(self, event: RenderDataEvent) -> None: pass
    def render_detail_view(self, event: DetailViewEvent) -> None: pass
    def render_envs_list(self, event: EnvsListEvent) -> None: pass
    def render_spinner_start(self, event: SpinnerStartEvent) -> None: pass
    def render_spinner_end(self, event: SpinnerEndEvent) -> None: pass
    def render_fetch_section_start(self, event: FetchSectionStartEvent) -> None: pass
    def render_fetch_task_start(self, event: FetchTaskStartEvent) -> None: pass
    def render_fetch_task_progress(self, event: FetchTaskProgressEvent) -> None: pass
    def render_fetch_task_end(self, event: FetchTaskEndEvent) -> None: pass
    def render_fetch_section_end(self, event: FetchSectionEndEvent) -> None: pass

    # Retained as synchronous query (not an event):
    @abstractmethod
    def prompt(self, message, choices, default) -> str: ...

    # --- Deprecated (pending removal per CEP 9) ---
    # render(), detail_view(), envs_list(),
    # progress_bar(), progress_bar_context_manager(), spinner()
    # Each decorated with @deprecated(..., remove_in="27.9")
```

No-op defaults (rather than `@abstractmethod`) mean existing third-party renderers
continue to work without changes during the deprecation window.

---

## Module-Level API in `conda/reporters.py`

The public call surface is preserved. `get_spinner()` returns a context manager
(same shape as today); `get_progress_bar()` returns a `ProgressBarBase`-compatible
shim that emits events internally. Callers see no change at their import sites.

```python
# Unchanged call shape — emits events internally:

def get_spinner(message: str, fail_message: str = "failed\n") -> AbstractContextManager:
    """Returns a context manager that emits SpinnerStart/End events."""

def render(data, style: str | None = None, **kwargs) -> None:
    """Emits RenderDataEvent or DetailViewEvent or EnvsListEvent."""

def confirm_yn(message="Proceed", default="yes", dry_run=None) -> bool:
    """Delegates to get_reporter().prompt(). Unchanged behavior."""

# Progress bar API — returns a shim that emits events:
def get_progress_bar(description: str, **kwargs) -> ProgressBarBase:
    """
    Returns an EventProgressBar: a ProgressBarBase subclass whose
    update_to/finish/close methods emit FetchTask* events to the reporter.
    Deprecated: callers should migrate to get_reporter().send(FetchTask*Event).
    """

def get_progress_bar_context_manager() -> AbstractContextManager:
    """
    Emits FetchSectionStart/End events. Returns a context manager.
    Deprecated: migrate to explicit FetchSection* events.
    """
```

`get_progress_bar()` returns an `EventProgressBar` adapter — a `ProgressBarBase`
subclass that, on each method call, emits the corresponding event to the reporter.
This lets `package_cache_data.py` and other callers migrate gradually.

---

## `ConsoleReporterRenderer` — After Refactor

`TQDMProgressBar`, `QuietProgressBar`, `Spinner`, and `QuietSpinner` become
private to the module (prefixed `_` or moved to a private submodule). They are
no longer part of the public plugin API.

The renderer holds its own internal state for active fetch sessions:

```python
class ConsoleReporterRenderer(ReporterRendererBase):

    def __init__(self) -> None:
        self._fetch_bars: dict[int, _TQDMProgressBar | _QuietProgressBar] = {}

    @property
    def _animations_disabled(self) -> bool:
        return context.quiet or not is_tty() or term_dumb()

    def render_fetch_section_start(self, event: FetchSectionStartEvent) -> None:
        if not context.verbose and not context.quiet and not context.json:
            print("\nDownloading and Extracting Packages:",
                  end="\n" if is_tty() and not term_dumb() else " ...working...")

    def render_fetch_task_start(self, event: FetchTaskStartEvent) -> None:
        description = _format_fetch_description(event.name, event.version, event.size)
        if self._animations_disabled:
            bar = _QuietProgressBar(description)
        else:
            bar = _TQDMProgressBar(description)
        self._fetch_bars[event.task_id] = bar

    def render_fetch_task_progress(self, event: FetchTaskProgressEvent) -> None:
        bar = self._fetch_bars.get(event.task_id)
        if bar:
            bar.update_to(event.fraction)

    def render_fetch_task_end(self, event: FetchTaskEndEvent) -> None:
        bar = self._fetch_bars.get(event.task_id)
        if bar:
            bar.finish()
            bar.refresh()

    def render_fetch_section_end(self, event: FetchSectionEndEvent) -> None:
        for bar in self._fetch_bars.values():
            bar.close()
        self._fetch_bars.clear()
        if not context.verbose and not context.quiet and not context.json:
            if is_tty() and not term_dumb():
                print("\r")
            else:
                print(" done")

    def render_spinner_start(self, event: SpinnerStartEvent) -> None:
        spinner = _Spinner(event.message, event.fail_message) \
                  if not self._animations_disabled \
                  else _QuietSpinner(event.message, event.fail_message)
        # Store by message key for retrieval in render_spinner_end
        self._spinners[event.message] = spinner
        spinner.__enter__()

    def render_spinner_end(self, event: SpinnerEndEvent) -> None:
        spinner = self._spinners.pop(event.message, None)
        if spinner:
            spinner.__exit__(None if event.success else Exception, None, None)

    def render_data(self, event: RenderDataEvent) -> None:
        text = str(event.data)
        if not text.endswith("\n"):
            text += "\n"
        sys.stdout.write(text)

    # ... detail_view, envs_list similarly
```

The description formatting logic currently in `package_cache_data._progress_bar()`
moves to a private helper `_format_fetch_description()` in `console.py` (or a
shared utility). The calling code passes raw `name`, `version`, `size` on the
event; the renderer decides the display format.

---

## `package_cache_data.py` — After Migration

The `execute()` method simplifies substantially:

```python
def execute(self):
    reporter = get_reporter()

    reporter.send(FetchSectionStartEvent())

    with ThreadPoolExecutor(...) as fetch_executor, \
         ThreadPoolExecutor(...) as extract_executor:

        for prec_or_spec, (cache_action, extract_action) in ...:
            task_id = id(prec_or_spec)
            reporter.send(FetchTaskStartEvent(
                task_id=task_id,
                name=prec_or_spec.name or "",
                version=prec_or_spec.version or "",
                size=getattr(prec_or_spec, "size", None),
            ))
            fetch_executor.submit(do_cache_action, prec_or_spec,
                                  cache_action, task_id, ...)
    ...
    reporter.send(FetchSectionEndEvent(success=not exceptions))
```

`do_cache_action` and `do_extract_action` receive `task_id: int` instead of
`progress_bar: ProgressBarBase`. They call:

```python
reporter.send(FetchTaskProgressEvent(task_id, pct * download_total))
reporter.send(FetchTaskEndEvent(task_id, success=True))
```

`is_tty()`, `term_dumb()`, `context.quiet`, `context.verbose` are gone from this
module.

---

## Thread Safety

`CondaReporter._lock` serializes all fetch progress events. This is correct
because multiple download threads emit `FetchTaskProgressEvent` concurrently;
tqdm's internal state is not always re-entrant under concurrent `update()` calls
from different threads even if each bar is distinct.

Events outside `_THREAD_SAFE_EVENTS` (spinners, output) are not locked. Spinners
are always called from the main thread. Output (`render_data`) is assumed
single-threaded at the call site.

The renderer (`ConsoleReporterRenderer`) must not acquire its own separate locks
on the same state — `CondaReporter` is the single synchronization point.

---

## Deprecation Plan (CEP 9)

Target pending-deprecation in the next regular release after this lands.
Target removal in `27.9` (the next September deprecation release after two
regular releases of pending deprecation).

Items deprecated:
- `conda.reporters.get_progress_bar()` → emit `FetchTask*` events directly
- `conda.reporters.get_progress_bar_context_manager()` → emit `FetchSection*` events
- `conda.reporters.get_spinner()` → kept as-is (same shape, event-backed), callers need not change
- `conda.plugins.types.ProgressBarBase` → internal to renderer implementations
- `conda.plugins.types.SpinnerBase` → internal to renderer implementations
- `ReporterRendererBase.progress_bar()` → implement `render_fetch_task_*` instead
- `ReporterRendererBase.spinner()` → implement `render_spinner_*` instead
- `ReporterRendererBase.progress_bar_context_manager()` → implement `render_fetch_section_*` instead
- `ReporterRendererBase.render()` → implement `render_data()` instead
- `ReporterRendererBase.detail_view()` → implement `render_detail_view()` instead
- `ReporterRendererBase.envs_list()` → implement `render_envs_list()` instead

`get_spinner()` is kept with the same call shape (context manager) — internally
backed by events rather than returning a `SpinnerBase`. It is not deprecated
because callers see no behavioral change.

`confirm_yn()` is unchanged — not deprecated.

---

## `RichReporterRenderer` — After Refactor (`conda-rich/`)

### Current coupling problem

`conda-rich`'s current design has a hard coupling between
`progress_bar_context_manager()` and `RichProgressBar`. The context manager
yields a `rich.progress.Progress` instance, which must then be passed back into
`get_progress_bar()` as the `context_manager=` kwarg. `RichProgressBar.__init__`
checks `isinstance(context_manager, Progress)` and raises `CondaError` if it is
missing. This is the most fragile point in the existing plugin API — the `Progress`
object has to travel from the renderer outward through `reporters.py` and back in
via a kwargs channel that no other backend uses.

Under the event model this coupling is eliminated. The renderer owns the `Progress`
object entirely; it never leaves the renderer.

### After: `RichReporterRenderer` state and handlers

```python
class RichReporterRenderer(ReporterRendererBase):

    def __init__(self) -> None:
        self._progress: Progress | None = None
        self._task_ids: dict[int, TaskID] = {}  # task_id → rich TaskID
        self._spinners: dict[str, Live] = {}     # message → Live context

    def render_fetch_section_start(self, event: FetchSectionStartEvent) -> None:
        console = Console(file=sys.stdout)
        self._progress = Progress(transient=True, console=console)
        self._task_ids = {}
        self._progress.start()

    def render_fetch_task_start(self, event: FetchTaskStartEvent) -> None:
        if self._progress is None:
            return  # no-op if section was never started (defensive)
        description = f"{event.name}-{event.version}"
        rich_task_id = self._progress.add_task(description, total=1)
        self._task_ids[event.task_id] = rich_task_id

    def render_fetch_task_progress(self, event: FetchTaskProgressEvent) -> None:
        if self._progress is None:
            return
        rich_task_id = self._task_ids.get(event.task_id)
        if rich_task_id is not None:
            self._progress.update(rich_task_id, completed=event.fraction)

    def render_fetch_task_end(self, event: FetchTaskEndEvent) -> None:
        if self._progress is None:
            return
        rich_task_id = self._task_ids.get(event.task_id)
        if rich_task_id is not None:
            self._progress.update(rich_task_id, completed=1.0)
            self._progress.stop_task(rich_task_id)

    def render_fetch_section_end(self, event: FetchSectionEndEvent) -> None:
        if self._progress is not None:
            self._progress.stop()
            self._progress = None
            self._task_ids.clear()

    def render_spinner_start(self, event: SpinnerStartEvent) -> None:
        if context.quiet:
            sys.stdout.write(f"{event.message}: ...working... ")
            sys.stdout.flush()
        else:
            progress = Progress(
                TextColumn("[progress.description]{task.description}"),
                SpinnerColumn("aesthetic"),
            )
            live = Live(progress, transient=True)
            live.__enter__()
            progress.add_task(event.message, start=False)
            self._spinners[event.message] = live

    def render_spinner_end(self, event: SpinnerEndEvent) -> None:
        if context.quiet:
            sys.stdout.write("done\n" if event.success else f"{event.fail_message}\n")
            sys.stdout.flush()
        else:
            live = self._spinners.pop(event.message, None)
            if live is not None:
                live.console.print(f"{event.message} (done)")
                live.__exit__(None, None, None)

    def render_detail_view(self, event: DetailViewEvent) -> None:
        # existing detail_view logic, writes to stdout
        ...

    def render_envs_list(self, event: EnvsListEvent) -> None:
        # existing envs_list logic using Console.capture()
        ...

    def prompt(self, message="Continue?", choices=("yes", "no"),
               default="yes") -> str:
        return Prompt.ask(message, choices=list(choices), default=default)
```

Key differences from current implementation:
- `_progress` is owned by the renderer, never exposed outside it.
- `_QuietProgressBar` disappears — the `context.quiet` branch in
  `render_fetch_task_start` simply skips task registration (or writes a
  single-line status, matching the current `QuietProgressBar` behavior).
- `render_spinner_start/end` absorbs both `RichSpinner` and `QuietSpinner`
  logic into a single pair of methods, branching on `context.quiet`.
- `RichProgressBar`, `RichSpinner`, `QuietProgressBar`, `QuietSpinner` become
  unnecessary and are removed entirely.
- The `CondaError` guard in `RichProgressBar.__init__` is eliminated — the
  renderer controls both section start and task start, so the invariant is
  enforced structurally.

### conda-rich test suite changes

The existing tests import internal classes directly:

```python
from conda_rich.hooks import (
    QuietProgressBar, QuietSpinner, RichSpinner, RichProgressBar, ...
)
```

These classes are removed, so the tests need to be rewritten to test at the
renderer method level. The new tests:

- Call `renderer.render_fetch_section_start(FetchSectionStartEvent())` and assert
  `renderer._progress` is a `Progress` instance.
- Call `renderer.render_fetch_task_start(...)` and assert a task was added.
- Call `renderer.render_fetch_task_progress(...)` and assert progress updated.
- Call `renderer.render_fetch_section_end(...)` and assert `_progress` is cleared.
- Call `renderer.render_spinner_start(...)` and `render_spinner_end(...)` and
  assert expected output (using `capsys`).
- Test quiet-mode branches by patching `context.quiet = True`.

The `test_rich_reporter_renderer_progress_bar_context_manager` test (which
verified the old `Progress` kwarg contract) is removed — the contract it tested
no longer exists.
