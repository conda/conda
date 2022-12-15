from __future__ import annotations

from . import archspec, cuda, linux, osx, windows

#: The list of virtual package plugins for easier registration with pluggy
plugins = [archspec, cuda, linux, osx, windows]
