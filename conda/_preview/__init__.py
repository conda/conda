# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Private namespace for conda preview features.

This package contains opt-in preview features that are not yet part of the
stable conda API. Code here may change or be removed across any release without
deprecation notices.

Conventions
-----------
- Each preview lives in its own subdirectory named after its label, with hyphens
  replaced by underscores (e.g. ``env-setup`` → ``env_setup/``).
- Each preview's ``__init__.py`` must expose:
  - ``PREVIEW_LABEL: str`` — the kebab-case label users put in ``context.preview``.
  - ``register(context)`` — called once after the final ``context.__init__()`` in
    ``main_subshell()`` when this preview is enabled.
- Each preview may mirror conda's ``cli/`` module structure under its own ``cli/``
  subdirectory. Modules there are discovered dynamically by ``do_call()`` and require
  no registration — adding ``cli/main_update.py`` is sufficient.

Graduation path
---------------
When a preview becomes the default behaviour, its code moves from ``_preview/`` into
the main conda tree, the label gets a deprecation notice, and the subdirectory is
removed.
"""
