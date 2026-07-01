# Requirements: Reporter Event System

## Problem

Currently, there is a high level of coupling in the code base for conda when it comes to printing stdout to the terminal or when conda is running in a script or CI. While this works okay in its current state, as we move to add different execution backends to conda (i.e. py-rattler), this high coupling in output rendering makes this work tedious. The maintainers also feel that not addressing this high level of coupling will lead to implementations that will be difficult to maintain later because they must work around deficiencies of our current design.

## Solution

We propose introducing an event architecture for reporter backends. The [reporter backends plugin hook](https://docs.conda.io/projects/conda/en/stable/dev-guide/plugins/reporter_backends.html) was initially conceived of as a widget based (e.g. spinners, progress bars, etc.) approach to allow the maintainers to easily introduce new user interfaces. While this approach was a step in the right direction, it did not address the coupling issue mentioned above.

This new system will modify the reporter backend API so that instead of using display widgets directly in the procedural code, callers will send events that will be dispatched via various methods. The end result allows reporter backend plugins to decide what to do with these events.

The work itself will involve creating the event based API for reporter backend and then refactoring existing code in conda to use it. The work will be limited in scope and only include the code paths for install/create/update/remove. We will be deprecating old code paths as part of this work to appropriately retire unnecessary parts of the existing reporter backend API.

A proof of concept for this work can be found here:

* [Draft design for an event based reporter backend API #16239](https://github.com/conda/conda/pull/16239)

## Background

Existing epic for reporter backend work:

* [Refactor conda to allow for configurable output backends #13707](https://github.com/conda/conda/issues/13707)

## Functional Requirements

### FR-1: Event Type Definitions

**Description:** The system must define a set of typed, immutable events that represent the distinct states and transitions in the install/create/update/remove workflows. Events must cover data rendering, environment listing, spinner lifecycle, and package fetch/extract lifecycle.

**Acceptance Criteria:**
- A defined set of event types exists as a stable, importable API.
- Each event type carries only the semantic data relevant to that event (e.g., package name, version, size for fetch events) and no rendering details.
- Event instances are immutable once constructed.
- All defined event types are accessible from a single, documented location.

**Rationale:** A well-defined, stable set of event types forms the contract between business logic and rendering. Immutability prevents renderers from accidentally mutating shared state, which is especially important in threaded contexts.

---

### FR-2: Central Event Dispatch

**Description:** A central dispatcher must accept events from calling code and route them to the appropriate rendering method on the active reporter backend. The dispatcher must be the single point of coordination between business logic and renderer plugins.

**Acceptance Criteria:**
- Calling code can emit any defined event type through the dispatcher without needing a direct reference to the active renderer.
- The dispatcher correctly routes each event type to the corresponding renderer method.
- The dispatcher is accessible via a stable module-level interface.
- Events that may be emitted concurrently (e.g., per-package fetch progress) are handled safely under concurrent conditions.

**Rationale:** Centralizing dispatch eliminates the need for business logic to know anything about the active renderer, how it is selected, or how it manages its internal state.

---

### FR-3: Renderer Plugin Contract

**Description:** The reporter renderer plugin contract must be updated to expose a rendering method for each defined event type. Default no-op implementations must be provided so that existing third-party renderers do not break when the new event types are introduced.

**Acceptance Criteria:**
- For every event type defined in FR-1, a corresponding method exists on the base renderer class.
- The default implementation of each new rendering method is a no-op, requiring no action from existing renderer implementations.
- The plugin contract does not expose any lifecycle management responsibilities to the renderer (e.g., the renderer does not decide when to start or stop a fetch session — it only responds to events).
- The renderer base class includes documentation indicating which methods should be implemented for new plugins.

**Rationale:** No-op defaults preserve backward compatibility for all existing third-party plugins while establishing a clear, forward-looking contract for what new implementations should provide.

---

### FR-4: Removal of Rendering Logic from Business Logic

**Description:** Code in the install/create/update/remove paths must not contain rendering or terminal-detection logic. TTY checks, progress bar construction, animation gating, and output formatting must not appear in non-rendering modules.

**Acceptance Criteria:**
- The install/create/update/remove code paths emit events only; they do not reference any renderer, widget, or terminal state.
- Terminal detection (e.g., TTY detection, dumb terminal checks) is not performed outside of renderer implementations.
- The event payload sent by callers contains only semantic data; it does not contain formatting hints or layout parameters.

**Rationale:** This is the primary goal of the refactor. Rendering logic in business code is the root cause of the coupling that makes it difficult to introduce alternative execution backends cleanly.

---

### FR-5: Backward Compatibility via Deprecation

**Description:** Existing public API symbols that are superseded by the event-based API must remain functional through a deprecation period, emitting appropriate deprecation warnings when used. They must not be removed until the planned removal release.

**Acceptance Criteria:**
- All superseded public API symbols issue a deprecation warning when called.
- The deprecation warning specifies the planned removal version.
- Third-party renderer plugins that implement only the legacy renderer methods continue to function (with warnings) through the deprecation period.
- No deprecated symbol is removed before its announced removal release.

**Rationale:** conda has an established deprecation policy (CEP 9) that gives downstream plugin authors time to migrate. Breaking changes without notice would erode trust in the plugin API.

---

### FR-6: Built-in Renderer Implementations

**Description:** The built-in console and JSON renderer backends must implement the new event-based rendering methods, producing output consistent with their current behavior.

**Acceptance Criteria:**
- The console renderer produces human-readable output (progress bars, spinners, formatted text) in response to the defined events, consistent with the existing terminal output.
- The JSON renderer produces machine-readable output in response to the defined events, consistent with the existing JSON output format.
- Both renderers pass the existing integration test suite for the install/create/update/remove workflows.

**Rationale:** The refactor must not regress observable output behavior. Users and tooling that rely on current output formats should not be impacted.

## Non-Functional Requirements

- **Extensibility:** Adding a new event type for a future workflow must not require changes to existing renderer implementations.
- **Testability:** Business logic and rendering logic must be independently testable. It must be possible to test the install/create/update/remove code paths by observing emitted events without involving any renderer.
- **Performance:** The dispatch layer must not introduce meaningful latency or memory overhead to the install/create/update/remove workflows.
- **Thread safety:** The system must remain correct under concurrent event emission (e.g., parallel package downloads emitting progress events simultaneously).
- **Observability:** The active renderer must receive sufficient information in each event to produce a complete, accurate output without needing to query external state.
- **Compatibility:** The system must remain compatible with the existing `conda_reporter_backends` plugin hook registration mechanism.

## Constraints and Dependencies

- **Scope:** The refactor is limited to the install/create/update/remove code paths. Other commands (`conda list`, `conda config`, `conda search`, etc.) are explicitly out of scope for this change.
- **Deprecation schedule:** All legacy API symbols must follow the conda deprecation policy (CEP 9) and must not be removed before the planned deprecation release.
- **Plugin hook stability:** The `conda_reporter_backends` hookspec and the `CondaReporterBackend` registration mechanism must not change as part of this work.
- **Third-party plugins:** Third-party renderer plugins outside this repository are not required to migrate in this change. They will receive the deprecation window to do so.
- **Python version:** The implementation must be compatible with the Python versions currently supported by conda.
- **Dependency on `conda-rich`:** The in-repository `conda-rich` plugin is in scope for migration as part of this work, and its migration serves as a validation of the new API design for third-party plugins.

## Timeline

The current version is `26.5.x`. Phases 1 and 2 are already substantially complete in the working tree. The remaining work spans Phases 3–6, with Phase 7 deferred to a future deprecation release.

| Phase | Description | Target Release | Notes |
|---|---|---|---|
| 1–2 | Infrastructure + `package_cache_data.py` migration | `26.7` | Largely done; needs test coverage and review |
| 3 | Spinner call sites | `26.7` | Low risk; `get_spinner()` call shape is unchanged |
| 4 | `conda-rich` migration | `26.9` | Most involved phase; rich renderer state management is non-trivial |
| 5 | Output render call sites (`render()`) | `26.9` | Mechanical; dependent on Phase 4 validation |
| 6 | Deprecation markers + changelog | `26.9` | Must land before the September deprecation release (`26.9`) to be official |
| 7 | Removal of deprecated symbols | `27.9` | Separate change; two deprecation cycles after `26.9` per CEP 9 |

**Key date constraint:** Phase 6 must land by the `26.9` release (September 2026) for the deprecation to be official per CEP 9. That gives roughly one regular release cycle (`26.7`) for the infrastructure to stabilize before the deprecation is formally declared.

## Success Metrics

**Correctness**
- All existing tests for the install/create/update/remove workflows pass without modification.
- No regressions in console or JSON output format as verified by integration tests.
- The `conda-rich` test suite is fully replaced and passes against the new `render_*` API.

**Decoupling**
- Zero references to `is_tty()`, `term_dumb()`, `context.quiet`, or any renderer/widget type remain in `package_cache_data.py`, `solve.py`, `link.py`, or `install.py` after migration.
- The `conda.reporters` module is the only non-renderer import site for event types in the install/create/update/remove paths.

**API stability**
- All superseded public symbols (`get_progress_bar`, `get_progress_bar_context_manager`, `ProgressBarBase`, `SpinnerBase`, and the legacy `ReporterRendererBase` methods) emit deprecation warnings targeting `27.9`.
- A third-party renderer that implements only the legacy abstract methods continues to function (with warnings) through the deprecation period — verifiable with a minimal plugin fixture in the test suite.

**Extensibility**
- A new event type can be added (as a new frozen dataclass + a new `render_*` no-op default) without modifying any existing renderer implementation — verifiable by adding a test-only event type in the test suite.

**Thread safety**
- A concurrent stress test emitting `FetchTaskProgressEvent` from multiple threads simultaneously produces no exceptions, no deadlocks, and the correct total call count on the renderer.
