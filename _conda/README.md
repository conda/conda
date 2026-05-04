Top-level `_conda`. Submodules of `_conda` must have the option of running
without importing anything from `conda` (even `conda.__init__.py`). This
directory should contain no `__init__.py`.

If you are an API user, stop! This module has no stability guarantees. Symbols
under `_conda` can be renamed or removed at any time. Instead, look for
re-exported API under `conda.*`.
