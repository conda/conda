`conda._private`. This directory should contain no `__init__.py` to avoid all
side-effects for any submodules.

If you are an API user, stop! This module has no stability guarantees. Symbols
under `_conda` can be renamed or removed at any time. Instead, look for
re-exported API under `conda.*`.
