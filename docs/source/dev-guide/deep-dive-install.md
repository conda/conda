<!--
Author: Jaime Rodríguez-Guerra <@jaimergp>, Quansight Labs.

Some resources that helped draft this document:
* https://speakerdeck.com/asmeurer/conda-internals
* https://www.anaconda.com/blog/understanding-and-improving-condas-performance
-->

In this document we will explore what happens in Conda from the moment a user types their
installation command until the process is finished successfully. For the sake of completeness,
we will consider the following situation:

* The user is running commands on a Linux x64 machine with a working installation of Miniconda.
* This means we have a `base` environment with `conda`, `python`, and their dependencies.
* The `base` environment is already preactivated for Bash. For more details on activation, check
  {ref}`Deep Dive: Activation`.

So... here we are:

```console
$ (base) ~/: conda info
... # TODO

$ (base) ~/: conda list
... # TODO
```

Ok, so... what happens when you run `conda install numpy`? Roughly, these steps:

1. Command-line interface
    * `argparse` parsers
    * Environment variables
    * Configuration files
    * Context initialization
    * Delegation of the task
2. Fetching the index
    * Retrieving all the channels and platforms
    * A note on channel priorities
3. Solving the install request
    * Requested packages + prefix state = list of specs
    * Index reduction (sometimes)
    * Running the solver
    * Post-processing the list of packages
4. Generating the transaction and the corresponding actions
5. Download and extraction
6. Integrity verification
7. Linking and unlinking files
8. Post-linking and post-activation tasks


## Command-line interface

<!-- This might be better in a separate deep-dive for the command line alone -->

First, a quick note on an implementation detail that might be not obvious.

When you type `conda install numpy` in your terminal, Bash took those three words and looked for a
`conda` command to pass a list of arguments `['conda', 'install', 'numpy']`. Before finding the
`conda` executable located at `CONDA_HOME/condabin`, it probably found the shell function defined
[here](https://github.com/conda/conda/blob/4.11.0/conda/shell/etc/profile.d/conda.sh#L62-L76). This
shell function runs the (de)activation logic on the shell if requested, or delegates over to
the actual Python entry-points otherwise. This part of the logic can be found in
[`conda/shell`](https://github.com/conda/conda/tree/4.11.0/conda/shell).

Once we are running the Python entry-point, we are in the
[`conda.cli`](https://github.com/conda/conda/tree/4.11.0/conda/cli) reigns. The function called by
the entry point is [`conda.cli.main:main()`](https://github.com/conda/conda/blob/4.11.0/conda/cli/main.py#L121).
Here, another check is done for `shell.*` subcommands, which generate the shell initializers you
see in `~/.bashrc` and others. If you are curious where his happens, it's
[`conda.activate`](https://github.com/conda/conda/blob/4.11.0/conda/activate.py).

Since our command is `conda install ...` we still need to arrive somewhere else. You will notice
that the rest of the logic is delegated to `conda.cli.main:_main()`, which will invoke the parser
generators, initialize the context and loggers, and, eventually, pass the argument list over to
the corresponding command function. These four steps are implemented in four functions/classes:

1. [`conda.cli.conda_argparse:generate_parser()`](https://github.com/conda/conda/blob/4.11.0/conda/cli/conda_argparse.py#L28):
  This uses `argparse` to generate the CLI. Each subcommand is initialized in separate functions.
  Note that the command-line options are not generated dynamically from the `Context` object, but
  annotated manually. If this is needed (e.g. `--repodata-fn` is exposed in `Context.repodata_fn`)
  the `dest` variable of each CLI option should [match the target attribute in the context object](https://github.com/conda/conda/blob/4.11.0/conda/cli/conda_argparse.py#L1484).
2. [`conda.base.context.Context`](https://github.com/conda/conda/blob/4.11.0/conda/cli/main.py#L75):
  Initialized taking into account, among other things, the parsed arguments from step above. This is
  covered in more detail in a separate deep dive: {ref}`deep-dive-context`.
3. [`conda.gateways.logging:initialize_logging()](https://github.com/conda/conda/blob/4.11.0/conda/gateways/logging.py#L162):
  Not too exciting and easy to follow. This part of the code base is more or less self-explanatory.
4. [`conda.cli.conda_argparse:do_call()] (https://github.com/conda/conda/blob/4.11.0/conda/cli/conda_argparse.py#L77):
  The argument parsing will populate a `func` value which contains the import path to the function
  responsible for that subcommand. For example, `conda install` is [taken care of](https://github.com/conda/conda/blob/4.11.0/conda/cli/conda_argparse.py#L775)
  by `conda.cli.main_install`. By design, all the modules reported by `func` must contain an
  `execute()` function that implements the command logic. `execute()` takes the parsed arguments
  and the parser itself as arguments. For example, in the case of `conda install`, `execute()` only
  [redirects](https://github.com/conda/conda/blob/4.11.0/conda/cli/main_install.py#L12) to a certain
  mode in `conda.cli.install`.

Let's go take a look at that module now. [`conda.cli.install:install()`](https://github.com/conda/conda/blob/4.11.0/conda/cli/install.py#L107)
implements the logic behind `conda create`, `conda install`, `conda update` and `conda remove`.
In essence, they all deal with the same task: changing which packages are present in an environment.
If you go and read that function, you will see there are several lines of code handling diverse
situations (new environments, clones, etc) before we arrive to the next section. We will not discuss
them here, but feel free to explore [that section](https://github.com/conda/conda/blob/4.11.0/conda/cli/install.py#L111-L223).

<!-- TODO: Maybe we do want to explain those checks? -->

## Fetching the index

WIP

## Solving the install request

WIP

## Generating the transaction and the corresponding actions

WIP

## Download and extraction

WIP

## Integrity verification

WIP

## Linking and unlinking files

WIP

## Post-linking and post-activation tasks

WIP
