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
- Preview command implementations should use conda's plugin framework. For
  subcommands, expose ``conda_subcommands`` hooks and register them through
  ``conda.plugins.previews``. Built-in command overrides are only allowed for
  bundled preview subcommands routed through conda's preview plugin.

Graduation path
---------------
When a preview becomes the default behaviour, its code moves from ``_preview/`` into
the main conda tree, the label gets a deprecation notice, and the subdirectory is
removed.
"""
