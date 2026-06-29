===========
Error Hints
===========

The ``conda_error_hints`` plugin hook allows plugins to contribute structured
next-step hints while conda renders a :class:`conda.CondaError`.

This hook is for user-facing remediation, not telemetry. Plugins should yield
:class:`~conda.plugins.types.CondaErrorHint` objects and should not print
directly. Conda appends the yielded hints to the error's existing guidance so
terminal and ``--json`` output stay consistent.

Example
-------

.. code-block:: python

   from conda import plugins
   from conda.exceptions import PackagesNotFoundInChannelsError


   @plugins.hookimpl
   def conda_error_hints(error):
       if isinstance(error, PackagesNotFoundInChannelsError):
           yield plugins.types.CondaErrorHint(
               text="Check whether the package exists on your expected channel.",
               hint_code="check_expected_channel",
           )

With that plugin installed, conda appends the hint to the normal terminal
guidance output:

.. code-block:: text

   PackagesNotFoundInChannelsError: The following packages are not available
   from current channels:
     - missing-package

   Next steps:
     - (check_expected_channel) Check whether the package exists on your expected channel.

The same hint is included in ``--json`` output:

.. code-block:: json

   {
     "error": "...",
     "exception_name": "PackagesNotFoundInChannelsError",
     "guidance": {
       "hints": [
         {
           "hint_code": "check_expected_channel",
           "text": "Check whether the package exists on your expected channel."
         }
       ],
       "hint_codes": ["check_expected_channel"]
     }
   }

Conda invokes each ``conda_error_hints`` implementation independently while
rendering expected errors. If one plugin raises or yields an invalid hint,
conda logs the plugin failure at DEBUG level and continues rendering the
original error plus any other valid hints.

Error hints vs. exception observers
-----------------------------------

Use ``conda_error_hints`` when a plugin wants to add user-facing next steps to
an expected :class:`conda.CondaError`. Hints are part of conda's normal error
guidance model: conda controls ordering, deduplicates by ``hint_code``, renders
them in the terminal ``Next steps`` section, and includes them in ``--json``
under ``guidance.hints`` and ``guidance.hint_codes``.

Use :doc:`exception_observers` when a plugin needs to observe failures for
telemetry, logging, demand tracking, or other side effects. Observers are
fire-and-forget callbacks modelled after :func:`sys.excepthook`: their return
value is ignored, and they should not mutate exceptions or print user-facing
messages.

API reference
-------------

.. autoapiclass:: conda.plugins.types.CondaErrorHint
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_error_hints
