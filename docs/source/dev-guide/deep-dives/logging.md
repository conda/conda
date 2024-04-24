(deep_dive_logging)=
# Logging

Logging in conda is based on the [Python logging framework](https://docs.python.org/3/library/logging.html).
In this guide, we'll describe the loggers and handlers used in conda, as well as how they are used.

## Logger hierarchy
Python logging uses loggers as the source of logging messages.
These loggers are organized as a single hierarchy defined by names given to individual loggers, with one nameless root logger.
Other logger names are given as dot separated strings, such that, for example, the logger named `a.b.c` has the parent `a.b`, which in turn has the parent `a`, which in turn has the root logger as its parent.
Python programs are free to use any name for loggers they like, but often the name will bear a relationship to the Python entity that is using it, most commonly there will be a module level logger, which is called `__name__`, i.e. `conda.<pkg>.<module>`, e.g. `conda.gateways.logging`.
This approach naturally arranges loggers used in a single code base into a hierarchy that follows the package structure.

Conda largely follows this approach, however, it also makes use of some additional loggers.

```{mermaid}
:caption: The conda logger hierarchy. Dotted lines represent relations with `propagate = False`.

flowchart LR
    root["&lt;root&gt;"] -.-> conda
    conda --> modules["conda.&lt;pkg&gt;.&lt;module&gt;"]
    conda -.-> conda.stdout -.-> conda.stdout.verbose
    conda -.-> conda.stderr
    conda -.-> conda.stdoutlog
    conda -.-> conda.stderrlog
    root --> auxlib
    root --> progress.update & progress.stop
```

The full hierarchy of all module level loggers is given below at {ref}`full-module-loggers`.

### The root logger

The root logger is not used directly as a logging target, but it is used as a building block in the configuration of the logging system.

### The `conda` subhierarchy

The `conda` subhierarchy consists of all loggers whose name starts with `conda.` and it is mostly configured via the `conda` logger itself in {func}`conda.gateways.logging.initialize_logging`.

Additionally, the following five loggers are used for other output.
These are likely to be replaced and should not be used in new code.
- `conda.stdout`
  - conda/exceptions.py:1255 -> print_conda_exception
  - conda/cli/common.py:201 -> stdout_json
  - conda/cli/main_config.py:322 -> print_config_item
  - conda/cli/main_config.py:365 -> execute_config
- `conda.stderr`
  - conda/exceptions.py:1255 -> print_conda_exception
  - conda/exceptions.py:1261 -> print_conda_exception
  - conda/cli/main_config.py:366 -> execute_config
  - conda/cli/install.py:53 -> check_prefix
  - conda/exception_handler.py:29 -> ExceptionHandler.write_out
- `conda.stdoutlog`
  - conda/resolve.py:47 -> Resolve.solve
  - conda/gateways/disk/create.py:79 -> make_menu (exception reporting)
- `conda.stderrlog`
  - conda/gateways/connection/adapters/s3.py:20 -> S3Adapter.send (reporting of import boto3 error)
  - conda/gateways/repodata/jlap/interface.py:50 -> Not used
  - conda/gateways/repodata/__init__.py:58 -> conda_http_errors
- `conda.stdout.verbose`
  - conda/instructions.py:50 -> PRINT_CMD

### Other loggers

Three more loggers are used in `conda`:
- `progress.update`
- `progress.stop`
- `auxlib`

## Handlers

### Auxlib

The `'auxlib'` logger get's a {class}`conda.auxlib.NullHandler`.

## Open questions

### Potential effect on other loggers

There are three other functions that use {func}`logging.getLogger` and hence might affect other loggers. They are {func}`conda.gateways.logging.set_file_logging` that is never used in the code base and the context managers {func}`conda.common.io.disable_logger` and {func}`conda.common.io.stderr_log_level`, which are only used in testing.

### Root logger in auxlib

In {module}`conda.auxlib.logz`, the root logger is modified.
