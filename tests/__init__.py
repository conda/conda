# This is just here so that tests is a package, so that dotted relative
# imports work.
from conda.gateways.logging import initialize_logging
initialize_logging()

# Attempt to move any conda entries in PATH to the front of it.
# IDEs have their own ideas about how PATH should be managed and
# they do dumb stuff like add /usr/bin to the front of it
# meaning conda takes a submissve role and the wrong stuff
# runs (when other conda prefixes get activated they replace
# the wrongly placed entries with newer wrongly placed entries).
#
# Note, there's still condabin to worry about here, and also should
# we not remove all traces of conda instead of just this fixup?
# Ideally we'd have two modes, 'removed' and 'fixed'. I have seen
# condabin come from an entirely different installation than
# CONDA_PREFIX too in some instances and that really needs fixing.

import os
if 'CONDA_PREFIX' in os.environ:
    from conda.activate import (PosixActivator, CmdExeActivator)
    activator = PosixActivator()
    # But why not just use _replace_prefix_in_path? => because moving
    # the entries to the front of PATH is the goal here, not swapping
    # x for x (which would be pointless anyway).
    p = activator._remove_prefix_from_path(os.environ['CONDA_PREFIX'])
    os.environ['PATH'] = os.pathsep.join(p)
    activator = PosixActivator()
    p = activator._add_prefix_to_path(os.environ['CONDA_PREFIX'])
    os.environ['PATH'] = os.pathsep.join(p)
