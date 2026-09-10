=======
Notices
=======

Conda's channel-notices feature (see :doc:`/commands/notices`) can be extended with
the ``conda_notices`` plugin hook. Write a plugin that yields
:class:`~conda.plugins.types.CondaNotice` entries and they will be merged into the
same notice pipeline as channel notices. Plugin notices are collected on every CLI
subcommand (via ``do_call``); channel notices are fetched as a side effect of
repodata loading (subject to the 24-hour fetch interval). An explicit
``conda notices`` always refreshes and displays.

Basic Plugin Notice
====================

A notice requires two things:

- **name**: A unique identifier for the notice, used for deduplication and
  viewed-notice tracking (see below)
- **message**: The text displayed to the user

Example of a basic plugin notice:

.. code-block:: python

   from datetime import datetime, timezone

   from conda import plugins
   from conda.base.constants import NoticeLevel


   @plugins.hookimpl
   def conda_notices():
       yield plugins.types.CondaNotice(
           name="my-plugin-deprecation-v1",
           message="This is an important message from my plugin.",
           level=NoticeLevel.WARNING,
           created_at=datetime.now(timezone.utc),
       )

``level`` defaults to ``NoticeLevel.INFO`` and may otherwise be ``WARNING`` or
``CRITICAL``. ``created_at`` and ``expired_at`` are optional ``datetime`` values used
only for display and expiry bookkeeping; they do not affect deduplication.

Controlling re-display with ``name``
=====================================

Unlike channel notices, plugin notices are **not** subject to the 24-hour
channel-notice fetch interval — ``conda_notices`` is called on every CLI
subcommand. Whether a user sees the same notice again is controlled entirely by
``name``:

- A **static** ``name`` (like the example above) is shown once, then suppressed on
  subsequent commands because it has already been marked as "viewed".
- A **dynamic** ``name`` (e.g. including a version string or date) causes the notice
  to reappear whenever the value changes, since it is treated as a new notice:

.. code-block:: python

   @plugins.hookimpl
   def conda_notices():
       yield plugins.types.CondaNotice(
           name=f"my-plugin-update-available-{latest_version()}",
           message=f"A new version ({latest_version()}) of my-plugin is available.",
       )

How plugin notices are displayed
==================================

Plugin notices are grouped and labeled by their source plugin (derived from the
hook implementation, not from the notice itself), for example::

   Plugin "my-plugin" has the following notices:
     [warning] -- Tue May 10 11:50:34 2022
     This is an important message from my plugin.

Users can show only plugin-sourced notices, skipping any channel-notices HTTP
fetch, with:

.. code-block:: bash

   conda notices --plugin

API Reference
==============

.. autoapiclass:: conda.plugins.types.CondaNotice
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_notices
