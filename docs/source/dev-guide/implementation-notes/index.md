# Implementation Notes

Notes on how specific conda subsystems are implemented. These pages are intended as a
reference for contributors and integrators.

```{toctree}
:maxdepth: 1
:hidden:

solver-state
sharded-repodata
```

```{eval-rst}
.. nav-glossary::

    :doc:`Solver state <solver-state>`
        A technical specification of the solver state: how the list of ``MatchSpec`` objects
        passed to the SAT solver is constructed from prefix state, history, pins, and other
        inputs.

    :doc:`Sharded repodata <sharded-repodata>`
        An overview of conda's implementation of CEP-16 sharded repodata, including the
        fetch algorithm, caching strategy, and the deliberate decision not to validate
        shard contents against their content-addressable SHA-256 filename hash.
```
