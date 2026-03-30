# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Attempt to move any conda entries in PATH to the front of it.
# IDEs have their own ideas about how PATH should be managed and
# they do dumb stuff like add /usr/bin to the front of it
# meaning conda takes a submissive role and the wrong stuff
# runs (when other conda prefixes get activated they replace
# the wrongly placed entries with newer wrongly placed entries).
#
# Note, there's still condabin to worry about here, and also should
# we not remove all traces of conda instead of just this fixup?
# Ideally we'd have two modes, 'removed' and 'fixed'. I have seen
# condabin come from an entirely different installation than
# CONDA_PREFIX too in some instances and that really needs fixing.
from __future__ import annotations

import os
import sys
from logging import getLogger
from os.path import join

log = getLogger(__name__)


def conda_move_to_front_of_PATH():
    if "CONDA_PREFIX" in os.environ:
        from ..activate import CmdExeActivator, PosixActivator

        if os.name == "nt":
            activator_cls = CmdExeActivator
        else:
            activator_cls = PosixActivator
        activator = activator_cls()
        # But why not just use _replace_prefix_in_path? => because moving
        # the entries to the front of PATH is the goal here, not swapping
        # x for x (which would be pointless anyway).
        p = None
        # It might be nice to have a parameterised fixture with choices of:
        # 'System default PATH',
        # 'IDE default PATH',
        # 'Fully activated conda',
        # 'PATHly activated conda'
        # This will do for now => Note, if you have conda activated multiple
        # times it could mask some test failures but _remove_prefix_from_path
        # cannot be used multiple times; it will only remove *one* conda
        # prefix from the *original* value of PATH, calling it N times will
        # just return the same value every time, even if you update PATH.
        p = activator._remove_prefix_from_path(os.environ["CONDA_PREFIX"])

        # Replace any non sys.prefix condabin with sys.prefix condabin
        new_p = []
        found_condabin = False
        for pe in p:
            if pe.endswith("condabin"):
                if not found_condabin:
                    found_condabin = True
                    if join(sys.prefix, "condabin") != pe:
                        condabin_path = join(sys.prefix, "condabin")
                        print(f"Incorrect condabin, swapping {pe} to {condabin_path}")
                        new_p.append(condabin_path)
                    else:
                        new_p.append(pe)
            else:
                new_p.append(pe)

        os.environ["PATH"] = os.pathsep.join(new_p)
        activator = activator_cls()
        p = activator._add_prefix_to_path(os.environ["CONDA_PREFIX"])
        os.environ["PATH"] = os.pathsep.join(p)
