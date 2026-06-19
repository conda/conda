# Proposal: Reporter Event System

## Summary

Refactor `conda.reporters` and `conda.plugins.reporter_backends` to replace the
current widget-factory model with an event-driven architecture. Calling code will
emit typed events to a global `CondaReporter` singleton, which dispatches them to
the active `ReporterRendererBase` implementation. This eliminates mixed rendering
responsibilities from business logic and establishes a clean, extensible boundary
between what happens in conda internals and how it is presented.

## Problem

The current reporter system conflates two distinct concerns:

**Calling code knows too much about rendering.** `conda.core.package_cache_data`
directly checks `is_tty()`, `term_dumb()`, `context.quiet`, and `context.verbose`
to decide whether animations are appropriate. It constructs progress bar
descriptions with specific formatting, passes layout kwargs (`position=`,
`leave=`, `context_manager=`) to `get_progress_bar()`, and manually prints
section headers and footers conditional on terminal state. These are all rendering
decisions that should belong exclusively to the reporter backend.

**The renderer API is a widget factory, not a rendering contract.** Methods like
`progress_bar()` and `spinner()` return objects that the caller must then manage
— calling `.update_to()`, `.finish()`, `.close()`. This inverts control: the
caller orchestrates the widget lifecycle instead of simply reporting what is
happening semantically.

**Duplication of terminal detection.** `is_tty()` and `term_dumb()` checks appear
in both `package_cache_data.py` (lines 814, 918, 955) and
`ConsoleReporterRenderer.animations_disabled` (console.py:241). Any new caller
repeats this pattern.

**The existing event sketch is incomplete.** `types.py` has a stub `RenderEvent`
NamedTuple and `send()`/`dispatch()` methods on `ReporterRendererBase`, but the
`dispatch()` body is missing and the design places routing responsibility inside
the plugin-authored renderer class — the wrong layer.

## Proposed Solution

Introduce a `CondaReporter` class in `conda/reporters.py` as the global singleton
coordinator. It ingests typed events from calling code, owns the dispatch table
that maps event types to renderer methods, manages cross-event state (active fetch
sessions, thread safety), and selects the active `ReporterRendererBase` based on
`context.console`.

`ReporterRendererBase` becomes a pure rendering contract: its methods receive
semantic events and produce output. It no longer acts as a factory for widget
objects and has no knowledge of event routing or dispatch.

Typed event dataclasses live in a new dedicated module,
`conda.plugins.reporter_backends.events`, which becomes the canonical registry of
all reportable events in conda.

The public API surface of `conda/reporters.py` is preserved as module-level
functions (`get_spinner()`, `get_progress_bar()`, `render()`, etc.) that delegate
to the singleton. The old functions are deprecated with a clear removal timeline,
giving third-party consumers a migration window.

## Goals

- Remove all rendering decisions (TTY checks, widget kwargs, terminal state) from
  `conda.core.package_cache_data` and other calling modules.
- Establish `CondaReporter` as the single point of coordination between calling
  code and output backends.
- Define a typed, documented event taxonomy in `conda.plugins.reporter_backends.events`.
- Ensure thread safety for progress events emitted from concurrent download
  threads.
- Provide a clear, CEP-9-compliant deprecation path for the existing public API
  (`ProgressBarBase`, `SpinnerBase`, `get_progress_bar()`, `get_spinner()`,
  `progress_bar()`, `spinner()` on `ReporterRendererBase`).
- Leave the public call-site API shape (`with get_spinner(...):`,
  `get_progress_bar(desc)`) unchanged so migrations are minimal renames rather
  than paradigm shifts.

## Scope

This change covers both the conda core reporter system and the in-repository
`conda-rich` plugin (`conda-rich/`). `conda-rich` is updated in the same change
so that the new `render_*` API has a working reference implementation alongside
the built-in console and JSON backends, and so its tests remain green after the
core API is refactored.

## Non-Goals

- Changing the pluggy hookspec or the `CondaReporterBackend` registration
  mechanism.
- Migrating third-party renderer plugins outside this repository (they get a
  deprecation window via the deprecated old API).
- Changing how `context.console` is set or how backends are selected.
- Removing `ProgressBarBase` or `SpinnerBase` in this change (deprecation only).

## Alternatives Considered

**Keep widget factories, just clean up duplication.** Would fix the `is_tty()`
duplication but not the inverted control problem. Callers still manage widget
lifecycles.

**Place dispatch inside `ReporterRendererBase`.** Initial direction in exploration.
Rejected: plugin authors would have to implement event routing logic, not just
rendering logic. These are different concerns with different change frequencies.

**Generic `RenderEvent(data: dict)` instead of typed events.** Simpler upfront
but loses type safety, IDE support, and discoverability. An event module that
grows large is manageable; a dict with arbitrary keys is not.
