# Deep dives

Detailed explorations of particularly complex subsystems in conda. These guides go
beyond the high-level architecture and explain the internal mechanics of specific
components.

```{toctree}
:maxdepth: 1
:hidden:

install
activation
context
condarc
solvers
solver-state
logging
sharded
```

```{nav-glossary}
:doc:`conda install <install>`
    A thorough walkthrough of what happens when you run ``conda install``: from
    parsing the command line through repodata fetching, the solver, transaction
    planning, and finally linking packages into the environment.

:doc:`conda init and conda activate <activation>`
    How conda manages shell integration, virtual environment activation and
    deactivation scripts, and the ``conda init`` bootstrap process.

:doc:`conda config and context <context>`
    The central ``Context`` object: how settings are loaded from defaults,
    ``.condarc`` files, environment variables, and command-line flags, and
    how they are merged with the correct precedence.

:doc:`Programmatic .condarc API <condarc>`
    How to programmatically read and write conda configuration files using
    the internal ``.condarc`` file API.

:doc:`Solvers <solvers>`
    Inside the solver black box: how conda constructs the ``MatchSpec`` inputs,
    drives the SAT solver, and handles conflicts and retries.

:doc:`Solver state <solver-state>`
    A technical reference for how the list of ``MatchSpec`` objects passed to the
    SAT solver is constructed from prefix state, history, pins, and other inputs.

:doc:`Logging <logging>`
    The loggers and handlers used throughout conda, how they are configured,
    and how to work with them during development and debugging.

:doc:`Sharded repodata <sharded>`
    How conda implements CEP-16 sharded repodata: the fetch loop, threading
    model, SQLite shard cache, and the deliberate decision not to validate shard
    contents against their content-addressable SHA-256 filename hash.
```
