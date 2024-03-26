(deep_dive_logging)=
# Logging in Conda

Logging in Conda is based on the [Python logging framework](https://docs.python.org/3/library/logging.html).
In this guide, we'll describe the loggers and handlers used in Conda, as well as how they are used.

## Logger hierarchy
Python logging uses loggers as the source of logging messages.
These loggers are organized as a single hierarchy defined by names given to individual loggers, with one nameless root logger.
Other logger names are given as dot separated strings, such that, for example, the logger named `a.b.c` has the parent `a.b`, which in turn has the parent `a`, which in turn has the root logger as its parent.
Python programs are free to use any name for loggers they like, but often the name will bear a relationship to the Python entity that is using it, most commonly there will be a module level logger, which is called `__name__`.
This approach naturally arranges loggers used in a single code base into a hierarchy that follows the package structure.

Conda largely follows this approach, however, it also makes use of some additional loggers.

### The root logger

The root logger is not used directly as a logging target, but it is used as a building block in the configuration of the logging system.

### The `conda` subhierarchy

The `conda` subhierarchy consists of all loggers whose name starts with `conda.` and it is mostly configured via the `conda` logger itself in :ref:`conda.gateways.logging:initialize_logging`.

Additionally, the following five loggers are used when logging output is immediately destined for the console, regardless of any other logging configuration that may happen in Conda or in user code.
- `conda.stdout`
- `conda.stderr`
- `conda.stdoutlog`
- `conda.stderrlog`
- `conda.stdout.verbose`

### Other loggers

Three more loggers are used in `conda`:
- `progress.update`
- `progress.stop`
- `auxlib`
