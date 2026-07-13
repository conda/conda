===========
Clean paths
===========

``conda clean`` can be extended with the ``conda_clean_paths`` plugin hook.
Plugins register removable file or directory paths; conda exposes each target
as a dedicated ``conda clean --<name>`` flag, then handles listing,
confirmation, dry-run, and removal.

Plugin targets are not included in ``conda clean --all``.

Basic clean path
================

A clean path requires:

- **name**: Identifier for the target (also used as the CLI flag, e.g.
  ``notices-cache`` becomes ``--notices-cache``)
- **find**: Callable that discovers paths to remove:
  ``find(target_prefix) -> paths``
- **summary** (optional): Help text shown in ``conda clean --help``

Each path may be a ``str`` or any other :data:`~conda.common.path.PathType`
(e.g. ``pathlib.Path``). Plugins only discover paths; they must not remove
files themselves.

Example:

.. code-block:: python

   from pathlib import Path

   from conda.plugins import hookimpl
   from conda.plugins.types import CondaCleanPath


   def find_example_cache(target_prefix: str):
       cache_dir = Path(target_prefix) / ".example-cache"
       if cache_dir.is_dir():
           yield cache_dir


   @hookimpl
   def conda_clean_paths():
       yield CondaCleanPath(
           name="example-cache",
           find=find_example_cache,
           summary="Remove example cache files.",
       )

Built-in target
===============

Conda registers a built-in ``notices-cache`` target that removes cached
channel notice files via ``conda clean --notices-cache``.

API Reference
=============

.. autoapiclass:: conda.plugins.types.CondaCleanPath
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_clean_paths
