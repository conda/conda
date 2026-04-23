==================
Exception Handlers
==================

The ``conda_exception_handlers`` plugin hook allows plugins to observe
exceptions as they pass through conda's error-reporting path. This is
useful for telemetry, logging, and demand tracking — for example,
reporting which packages users tried to install but could not find in
the configured channels.

Exception handler plugins are **purely observational** (modelled after
CPython's :func:`sys.excepthook`): they cannot suppress, modify, or
redirect the exception. Their return value is ignored. Any exception
raised inside a handler is caught and logged at DEBUG level, so a
buggy plugin can never disrupt conda.

Handlers fire for every exception conda handles: ``CondaError`` and
its subclasses, ``MemoryError``, ``KeyboardInterrupt``, ``SystemExit``,
and plain Python exceptions such as ``RuntimeError`` or ``KeyError``
that conda would otherwise report as an unexpected error. The
``run_for`` parameter selects which of those trigger a given handler;
see `Choosing a run_for scope`_ below.

Tutorial: reporting missing packages to channels
-------------------------------------------------

Suppose you maintain a private conda channel and want to know which
packages your users are looking for but cannot find. You can write a
small plugin that fires whenever a
:class:`~conda.exceptions.PackagesNotFoundInChannelsError` is raised
and sends a lightweight report to each channel.

Step 1 — write the hook
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python
   :caption: conda_missing_reporter/plugin.py

   from __future__ import annotations

   import logging
   from typing import TYPE_CHECKING

   from conda import plugins

   if TYPE_CHECKING:
       from conda.plugins.types import CondaExceptionInfo

   log = logging.getLogger(__name__)


   def report_missing(info: CondaExceptionInfo) -> None:
       """
       Send a fire-and-forget GET request to each channel's ``/missing``
       endpoint so that channel maintainers can track demand.

       Uses conda's built-in session so that proxy settings, SSL
       configuration, and per-channel auth are picked up automatically.
       """
       if info.offline or info.dry_run:
           return

       from conda.gateways.connection.session import get_session

       exc = info.exc_value

       specs = ",".join(str(s) for s in exc.packages)
       for url in {u.rstrip("/") for u in exc.channel_urls}:
           target = f"{url}/missing?specs={specs}"
           try:
               get_session(target).get(target, timeout=2)
           except Exception:
               log.debug("Failed to report to %s", target, exc_info=True)


   @plugins.hookimpl
   def conda_exception_handlers():
       yield plugins.types.CondaExceptionHandler(
           name="missing-package-reporter",
           hook=report_missing,
           run_for={"PackagesNotFoundInChannelsError"},
       )

``run_for`` accepts a set of exception class names. Matching uses the
exception's full `MRO`_, so parent class names automatically match
subclasses.

For non-``CondaError`` exceptions, the conda runtime fields on
:class:`~conda.plugins.types.CondaExceptionInfo` may be ``None`` (see
below).

.. _MRO: https://docs.python.org/3/glossary.html#term-method-resolution-order

Choosing a ``run_for`` scope
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pick the narrowest scope that covers the exceptions you care about:

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - ``run_for``
     - Captures
     - Typical use
   * - ``{"CondaError"}``
     - All conda errors and their subclasses (missing packages, solver
       failures, channel errors).
     - Plugins focused on conda's own errors — channel demand tracking,
       solver analytics.
   * - ``{"PackagesNotFoundError"}``
     - One error class and its subclasses.
     - Narrowly targeted integrations.
   * - ``{"Exception"}``
     - Every standard exception, including non-``CondaError`` types
       like ``RuntimeError`` or ``KeyError``. Excludes
       ``KeyboardInterrupt`` and ``SystemExit``.
     - Sensible default for error-tracking backends such as Sentry
       or Rollbar.
   * - ``{"BaseException"}``
     - Every exception, including ``KeyboardInterrupt`` and
       ``SystemExit``.
     - Diagnostics or auditing where every exit path matters.
   * - ``{"MemoryError"}``, ``{"KeyboardInterrupt"}``, ``{"SystemExit"}``
     - Specific non-``CondaError`` types.
     - Narrowly targeted handlers.
   * - ``{"CondaError", "MemoryError"}``
     - Union of scopes — the handler fires when any class in the
       exception's MRO matches any entry in the set.
     - Combining a domain scope with a specific non-conda type.

Step 2 — package and register
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Conda discovers plugins via `entry points`_. Add one to your
``pyproject.toml``:

.. code-block:: toml
   :caption: pyproject.toml

   [build-system]
   requires = ["setuptools", "setuptools-scm"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "conda-missing-reporter"
   version = "0.1.0"
   description = "Report missing packages to channel maintainers"
   requires-python = ">=3.10"
   dependencies = ["conda"]

   [project.entry-points."conda"]
   conda-missing-reporter = "conda_missing_reporter.plugin"

Install the package (``pip install -e .``) and the hook is active
the next time conda runs.

.. _entry points: https://packaging.python.org/en/latest/specifications/entry-points/

Step 3 — test it
^^^^^^^^^^^^^^^^^

You can test the plugin without packaging it by registering the plugin
class directly with the plugin manager:

.. code-block:: python

   import sys

   from conda import CondaError
   from conda.exceptions import PackagesNotFoundInChannelsError
   from conda.plugins.manager import CondaPluginManager


   class FakeReporter:
       """Collects exception info objects for assertions."""

       def __init__(self):
           self.calls = []

       @conda.plugins.hookimpl
       def conda_exception_handlers(self):
           yield conda.plugins.types.CondaExceptionHandler(
               name="fake-reporter",
               hook=self.calls.append,
               run_for={"PackagesNotFoundInChannelsError"},
           )


   pm = CondaPluginManager()
   reporter = FakeReporter()
   pm.register(reporter)

   exc = PackagesNotFoundInChannelsError(
       packages=["numpy"],
       channel_urls=["https://repo.anaconda.com/pkgs/main"],
   )
   try:
       raise exc
   except CondaError:
       _, exc_val, exc_tb = sys.exc_info()
       pm.invoke_exception_handlers(exc_val, exc_tb)

   assert len(reporter.calls) == 1
   info = reporter.calls[0]
   assert info.exc_value is exc
   assert info.exc_type is PackagesNotFoundInChannelsError

What the handler receives
--------------------------

Handlers are called with a single frozen
:class:`~conda.plugins.types.CondaExceptionInfo` dataclass.

The exception triple is always populated:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``exc_type``
     - The exception class.
   * - ``exc_value``
     - The exception instance. For ``CondaError`` subclasses, access
       domain attributes like ``exc_value.packages`` here.
   * - ``exc_traceback``
     - The traceback object.

The remaining fields describe the conda runtime state. They are
populated all-or-nothing: either the runtime was available and all
fields are set, or it wasn't and they're all ``None``. Check
``conda_version is not None`` to tell the two cases apart.
``active_prefix`` is the one exception — it can be ``None`` even
when the runtime is available (meaning no environment is active):

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``argv``
     - A frozen copy of :data:`sys.argv` at the time of the error.
   * - ``conda_version``
     - The conda version string.
   * - ``return_code``
     - The exit code conda will use for this error.
   * - ``active_prefix``
     - The currently active conda environment prefix, or ``None`` if no
       environment is active.
   * - ``target_prefix``
     - The prefix the command was operating on.
   * - ``channels``
     - The configured channel names at the time of error (canonical
       names, e.g. ``defaults``, ``conda-forge``).
   * - ``subdir``
     - The platform subdirectory (e.g., ``linux-64``, ``osx-arm64``).
   * - ``offline``
     - Whether conda is running in offline mode (``--offline``).
   * - ``dry_run``
     - Whether conda is running in dry-run mode (``--dry-run``).
   * - ``quiet``
     - Whether conda is running in quiet mode (``--quiet``).
   * - ``json``
     - Whether conda is running in JSON output mode (``--json``).

.. warning::

   Handlers run synchronously. ``exc_traceback`` is released as soon as
   dispatch returns, and keeping references to ``exc_value`` or
   ``exc_traceback`` can create reference cycles that prevent garbage
   collection. Capture or serialize any traceback data you need inside
   the callback — do not hand these objects off to a background thread
   or deferred queue.

Design notes
-------------

- **Observational only** — handlers cannot change conda's behavior.
  This follows CPython's :func:`sys.excepthook` model.
- **All exception types** — dispatch happens at the top of
  :meth:`~conda.exception_handler.ExceptionHandler.handle_exception`,
  before conda's own error-report dispatch, so handlers see every
  exception regardless of how conda would classify it. Use
  ``run_for`` to control scope.
- **Fault-tolerant** — any exception (including ``SystemExit``) raised
  by a handler is caught at the ``BaseException`` level, logged, and
  swallowed.
- **MRO-based matching** — ``run_for`` is checked against every class
  in the exception's method resolution order, so parent class names
  automatically match subclasses.
- **Frozen info object** — ``CondaExceptionInfo`` is a frozen
  dataclass, preventing plugins from mutating shared state.
- **Optional runtime fields** — conda-specific fields are ``None``
  when the runtime isn't initialized, following CPython's flat args
  pattern (``threading.ExceptHookArgs``, ``sys.UnraisableHookArgs``).

API reference
--------------

.. autoapiclass:: conda.plugins.types.CondaExceptionInfo
   :members:
   :undoc-members:

.. autoapiclass:: conda.plugins.types.CondaExceptionHandler
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_exception_handlers
