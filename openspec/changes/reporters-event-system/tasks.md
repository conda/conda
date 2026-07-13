# Tasks: Reporter Event System

## Phase 1 — Infrastructure (no caller changes)

### 1.1 Create `conda/plugins/reporter_backends/events.py`

Add a new module with all typed event dataclasses. All events are
`@dataclass(frozen=True)`.

Events to define:
- `RenderDataEvent(data: Any, style: str | None = None)`
- `DetailViewEvent(data: dict[str, str | int | bool])`
- `EnvsListEvent(prefixes: tuple, show_size: bool = False)`
- `SpinnerStartEvent(message: str, fail_message: str = "failed\n")`
- `SpinnerEndEvent(message: str, success: bool)`
- `FetchSectionStartEvent()`
- `FetchTaskStartEvent(task_id: int, name: str, version: str, size: int | None)`
- `FetchTaskProgressEvent(task_id: int, fraction: float)`
- `FetchTaskEndEvent(task_id: int, success: bool)`
- `FetchSectionEndEvent(success: bool)`

Also define `RenderEvent` as a `TypeAlias` union of all event types.

Remove the incomplete `RenderEvent` NamedTuple, `send()`, and `dispatch()`
stubs from `conda/plugins/types.py`.

### 1.2 Add `render_*` methods to `ReporterRendererBase`

In `conda/plugins/types.py`, add a no-op (non-abstract) default implementation
for each new renderer method. These must accept the corresponding event type
from `events.py`.

New methods (all default to `pass`):
- `render_data(event: RenderDataEvent) -> None`
- `render_detail_view(event: DetailViewEvent) -> None`
- `render_envs_list(event: EnvsListEvent) -> None`
- `render_spinner_start(event: SpinnerStartEvent) -> None`
- `render_spinner_end(event: SpinnerEndEvent) -> None`
- `render_fetch_section_start(event: FetchSectionStartEvent) -> None`
- `render_fetch_task_start(event: FetchTaskStartEvent) -> None`
- `render_fetch_task_progress(event: FetchTaskProgressEvent) -> None`
- `render_fetch_task_end(event: FetchTaskEndEvent) -> None`
- `render_fetch_section_end(event: FetchSectionEndEvent) -> None`

Mark the old abstract methods as pending deprecation using `conda.deprecations`:
`render()`, `detail_view()`, `envs_list()`, `progress_bar()`, `spinner()`,
`progress_bar_context_manager()`. Target removal: `27.9`.

Mark `ProgressBarBase` and `SpinnerBase` as pending deprecation, target `27.9`.

### 1.3 Add `CondaReporter` class to `conda/reporters.py`

Implement `CondaReporter` with:
- `__init__(self, renderer: ReporterRendererBase)`
- `_DISPATCH: dict[type, str]` — static mapping of event type → renderer method name
- `_THREAD_SAFE_EVENTS: frozenset[type]` — events requiring lock on dispatch
- `_lock: threading.Lock`
- `send(self, event: RenderEvent) -> None` — dispatches with optional locking
- `prompt(self, message, choices, default) -> str` — delegates to renderer

Add module-level singleton management:
- `_reporter: CondaReporter | None = None`
- `get_reporter() -> CondaReporter` — lazy initializer
- `reset_reporter() -> None` — clears singleton

Update `conda/base/context.py` to call `reset_reporter()` instead of
`_get_render_func.cache_clear()`.

### 1.4 Implement `render_*` methods in `ConsoleReporterRenderer`

In `conda/plugins/reporter_backends/console.py`:

- Move `TQDMProgressBar`, `QuietProgressBar`, `Spinner`, `QuietSpinner` to
  private names (prefix with `_`).
- Add `_fetch_bars: dict[int, ...]` and `_spinners: dict[str, ...]` instance
  state to `ConsoleReporterRenderer.__init__`.
- Move description formatting logic (currently in
  `package_cache_data._progress_bar()`) to a private helper
  `_format_fetch_description(name, version, size) -> str`.
- Implement all ten `render_*` methods, preserving current visual behaviour
  (tqdm bars, `animations_disabled` logic, section header/footer prints).

### 1.5 Implement `render_*` methods in `JSONReporterRenderer`

In `conda/plugins/reporter_backends/json.py`:

- Move `JSONProgressBar`, `JSONSpinner` to private names.
- Implement all ten `render_*` methods, preserving current JSON output format.
- `render_fetch_task_progress` emits the existing newline-delimited JSON format.

### 1.6 Write tests for Phase 1

- Unit tests for each event dataclass (construction, immutability).
- Unit tests for `CondaReporter.send()` dispatch — verify correct renderer method
  is called for each event type.
- Unit tests for `CondaReporter` thread safety — emit `FetchTaskProgressEvent`
  from multiple threads concurrently, assert no exceptions and correct call count.
- Unit tests for `ConsoleReporterRenderer` `render_*` methods with mocked tty
  state (TTY on, TTY off, quiet mode).
- Unit tests for `JSONReporterRenderer` `render_*` methods.

---

## Phase 2 — Migrate `package_cache_data.py` (proof-of-concept)

### 2.1 Update `ProgressiveFetchExtract.execute()`

Replace `get_progress_bar_context_manager()` and `get_progress_bar()` calls with
`get_reporter().send(FetchSection*/FetchTask* events)`.

Replace the manually printed section header (lines 812–825) and footer
(lines 917–921) with `FetchSectionStartEvent` and `FetchSectionEndEvent`.

Remove the `is_tty()`, `term_dumb()`, `context.quiet`, `context.verbose` checks
from `execute()` and `_progress_bar()`.

### 2.2 Update `do_cache_action()` and `do_extract_action()`

Change signature to accept `task_id: int` and `reporter: CondaReporter` instead
of `progress_bar: ProgressBarBase`.

Replace `progress_bar.update_to(...)` with
`reporter.send(FetchTaskProgressEvent(task_id, fraction))`.

Replace `progress_bar.update_to(1.0)` in `do_extract_action` with
`reporter.send(FetchTaskEndEvent(task_id, success=True))`.

### 2.3 Update `done_callback()`

Replace `progress_bar.finish()` and `progress_bar.refresh()` with
`reporter.send(FetchTaskEndEvent(task_id, success=...))`.

Remove `progress_bar` parameter; add `task_id: int` and `reporter: CondaReporter`.

### 2.4 Remove `_progress_bar()` static method

The description formatting logic moves to `_format_fetch_description()` in
`console.py` (task 1.4). Remove `ProgressiveFetchExtract._progress_bar()`.

### 2.5 Write tests for Phase 2

- Integration test: run `ProgressiveFetchExtract.execute()` against a mock
  package server, assert `FetchSectionStartEvent`, `FetchTaskStartEvent`,
  `FetchTaskProgressEvent`, `FetchTaskEndEvent`, `FetchSectionEndEvent` are
  all emitted in the correct order.
- Verify no `is_tty`, `term_dumb`, `context.quiet` references remain in
  `package_cache_data.py`.

---

## Phase 3 — Migrate spinner call sites

### 3.1 Back `get_spinner()` with events

In `conda/reporters.py`, rewrite `get_spinner()` to return a context manager
that emits `SpinnerStartEvent` on `__enter__` and `SpinnerEndEvent` on `__exit__`.
It must no longer call `_get_render_func("spinner")` or return a `SpinnerBase`.

The call shape `with get_spinner("message"):` is unchanged.

### 3.2 Verify all spinner call sites work unchanged

Run the test suite for:
- `conda/core/solve.py`
- `conda/core/link.py`
- `conda/cli/install.py`
- `conda/cli/main_search.py`
- `conda/notices/fetch.py`
- `conda/env/installers/pip.py`

No caller changes are required; this task confirms they all still work.

---

## Phase 4 — Migrate `conda-rich` (`conda-rich/conda_rich/hooks.py`)

### 4.1 Implement `render_*` methods in `RichReporterRenderer`

Add `__init__` with instance state: `_progress`, `_task_ids`, `_spinners`.

Implement:
- `render_fetch_section_start()` — creates and starts a `rich.progress.Progress`
  instance, stores as `self._progress`.
- `render_fetch_task_start()` — calls `self._progress.add_task()`, maps
  `event.task_id` → rich `TaskID` in `self._task_ids`.
- `render_fetch_task_progress()` — calls `self._progress.update()` with
  `completed=event.fraction`.
- `render_fetch_task_end()` — sets task to `completed=1.0` and calls
  `self._progress.stop_task()`.
- `render_fetch_section_end()` — calls `self._progress.stop()`, clears state.
- `render_spinner_start()` — if `context.quiet`, writes `"message: ...working... "`;
  otherwise creates a `rich.live.Live` context with a `Progress` spinner column,
  stores it in `self._spinners[event.message]`.
- `render_spinner_end()` — if `context.quiet`, writes `"done\n"` or
  `fail_message`; otherwise retrieves and exits the `Live` context, prints
  `"message (done)"`.
- `render_detail_view()` — contains the existing `detail_view()` rendering logic,
  writes to stdout directly.
- `render_envs_list()` — contains the existing `envs_list()` rendering logic
  using `Console.capture()`, writes to stdout.

All `render_*` handlers must guard defensively against `None` state (e.g.
`render_fetch_task_start` called without a prior `render_fetch_section_start`).

### 4.2 Remove internal widget classes from `conda-rich`

Delete `RichProgressBar`, `QuietProgressBar`, `RichSpinner`, and `QuietSpinner`
from `conda_rich/hooks.py`. Their logic is now absorbed into the `render_*`
methods. Remove the `CondaError` import if it is no longer used.

Remove the `progress_bar()`, `progress_bar_context_manager()`, `spinner()`,
`detail_view()`, and `envs_list()` methods from `RichReporterRenderer` (they will
be covered by the inherited no-op + deprecation from `ReporterRendererBase`).

### 4.3 Rewrite `conda-rich` test suite

The existing tests import removed classes (`RichProgressBar`, `QuietProgressBar`,
`RichSpinner`, `QuietSpinner`) and test the old factory API. Replace with tests
that exercise the `render_*` methods directly:

- `test_render_fetch_section_start` — asserts `renderer._progress` is a
  `Progress` instance after the call.
- `test_render_fetch_task_start` — asserts a task is registered in
  `renderer._task_ids`.
- `test_render_fetch_task_progress` — asserts the rich task's `completed`
  value is updated.
- `test_render_fetch_task_end` — asserts the task is stopped.
- `test_render_fetch_section_end` — asserts `renderer._progress` is `None` and
  `renderer._task_ids` is empty.
- `test_render_spinner_start_quiet` / `test_render_spinner_end_quiet` — patch
  `context.quiet = True`, assert expected stdout via `capsys`.
- `test_render_spinner_start_animated` / `test_render_spinner_end_animated` —
  assert a `Live` instance is stored/retrieved.
- `test_render_detail_view` — assert formatted string output (replaces
  `test_rich_reporter_renderer_detail_view`).
- `test_render_envs_list` — assert formatted string output (replaces
  `test_rich_reporter_renderer_env_list`).
- `test_conda_reporter_backends` — unchanged; verifies hookimpl registration.

Remove `test_rich_reporter_renderer_progress_bar`,
`test_rich_reporter_renderer_progress_bar_with_quiet`,
`test_rich_reporter_renderer_progress_bar_context_manager`,
`test_rich_reporter_renderer_spinner`, and
`test_rich_reporter_renderer_spinner_with_quiet` — these test the removed factory
API.

---

## Phase 5 — Migrate output render call sites

### 5.1 Back `render()` with `RenderDataEvent`

Rewrite `conda/reporters.render()` to emit `RenderDataEvent` through the
singleton instead of calling `_get_render_func(style)(data)` directly.

The `style` parameter maps to the event as `style` field. The renderer's
`render_data()` dispatches to `render_detail_view()` or `render_envs_list()`
based on `event.style`, or falls back to generic string output.

### 5.2 Verify output call sites unchanged

Confirm `conda/cli/common.py`, `conda/cli/main_info.py`, and other callers of
`render()` continue to work without modification.

---

## Phase 6 — Deprecation and cleanup

### 6.1 Deprecate old `reporters.py` functions

Apply `@deprecated(deprecate_in="current", remove_in="27.9", ...)` from
`conda.deprecations` to:
- `get_progress_bar()`
- `get_progress_bar_context_manager()`
- `_get_render_func()` (private, but referenced externally via `cache_clear`)

### 6.2 Remove `_get_render_func` external reference

After `reset_reporter()` is wired into `context.py` (task 1.3), remove the
`_get_render_func.cache_clear()` call and its import from `context.py`. Remove
`_get_render_func` from `reporters.py` entirely.

### 6.3 Add changelog entry

Add `news/` fragment (use the issue number as filename). Sections needed:
- Enhancements: new event system, `CondaReporter` singleton,
  `conda.plugins.reporter_backends.events` module.
- Deprecations: `ProgressBarBase`, `SpinnerBase`, `progress_bar()`,
  `spinner()`, `progress_bar_context_manager()`, `render()`, `detail_view()`,
  `envs_list()` on `ReporterRendererBase`; `get_progress_bar()`,
  `get_progress_bar_context_manager()` in `conda.reporters`.

---

## Phase 7 — Future (separate change, next deprecation release)

- Remove deprecated shims from `conda/reporters.py`.
- Remove deprecated abstract methods from `ReporterRendererBase`.
- Remove `ProgressBarBase` and `SpinnerBase` from `conda/plugins/types.py`
  (or retain with deprecation warning on import for one more cycle if
  third-party adoption requires it).
- Update any additional third-party plugins outside this repository to implement
  `render_*` methods.
