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
It's mostly ensuring that the destination prefix exists, whether we are creating a new environment
and massaging some command-line flags that would allow us to skip the solver (e.g. `--clone`).

<!-- TODO: Maybe we do want to explain those checks? -->

## Fetching the index

At this point, we are ready to start doing some work! All the previous code was telling us what to
do, and now we know. We want `conda` to _install_  `numpy` on our `base` environment. First thing
we need to know is where we can find packages with the name `numpy`. The answer is... the channels!

Users download packages from `conda` channels. These are normally hosted at `anaconda.org`. A channel
is essentially a directory structure with these elements:

```
<channel>
├── channeldata.json
├── index.html
├── <platform> (e.g. linux-64)
│   ├── current_repodata.json
│   ├── current_repodata.json.bz2
│   ├── index.html
│   ├── repodata.json
│   ├── repodata.json.bz2
│   ├── repodata_from_packages.json
│   └── repodata_from_packages.json.bz2
└── noarch
    ├── current_repodata.json
    ├── current_repodata.json.bz2
    ├── index.html
    ├── repodata.json
    ├── repodata.json.bz2
    ├── repodata_from_packages.json
    └── repodata_from_packages.json.bz2
```

The important bits are:

* A channel contains one or more platform-specific directories (`linux-64`, `osx-64`, etc), plus a
  platform-agnostic directory called `noarch`. In `conda` jargon, these are also referred as channel
  _subdirs_.
* Each _subdir_ contains, at least, a `repodata.json` file: a gigantic dictionary with _all_ the
  metadata for each package available on that platform.
* In most cases, the same subdirs also contain the `*.tar.bz2` files for each of the published
  packages. This is what `conda` downloads and extracts once solving is complete. The anatomy of
  these files is well defined, both in content and naming structure. See {ref}``.

Additionally, the channel main directory might contain a `channeldata.json` file, with channel-wide
metadata (this is, not specific per platform). Not all channels include this and, actually, it's not
really used these days. <!-- TODO: Check why and reasons for this file to exist -->

Since conda's philosophy is to keep all packages ever published around for reproducibility,
`repodata.json` is always growing, which presents a problem both for the download itself and the
solver engine. To reduce download times and bandwidth usage, `repodata.json` is also served as a
BZIP2 compressed file, `repodata.json.bz2`. This is what most `conda` clients end up downloading.

> Note on `current_repodata.json`: More _repodatas_ variations can be found in
> some channels, but they are mostly reduced versions of the main one for the sake of performance
> For example, `current_repodata.json` only contains the most recent version of each package, plus
> their dependencies. The rationale behind this optimization trick can be found [here](# TODO: ).

So, in essence, fetching the channel information means can be expressed in pseudo-code like this:

```python
platform = []
noarch = []
for channel in context.channels:
    platform_repodata = fetch_extract_and_read(channel.full_url / context.subdir / "repodata.json.bz2")
    platform.append(platform_repodata)
    noarch_repodata = fetch_extract_and_read(channel.full_url / "noarch" / "repodata.json.bz2")
    noarch.append(noarch_repodata)

```

In this example, `context.channels` has been populated through different, cascading mechanisms:

* The default settings as found in `~/.condarc` or equivalent.
* The `CONDA_CHANNELS` environment variable (rare usage).
* The command-line flags, such as `-c <channel>`, `--use-local` or `--override-channels`.
* The channels present in a command-line _spec_. Remember that users can say `channel::numpy`
  instead of simply `numpy` to require that numpy comes from that specific channel. That means that
  the repodata for such channel needs to be fetched too!

The items in `context.channels` are supposed to be `conda.models.channels.Channel` objects, but you
can also find strings that refer to their name, alias or full URL. In that case, you can use
`Channel` objects to parse and retrieve the full URL for each subdir using the `Channel.urls()`
method. Several helper functions can be found in `conda.core.index`, if needed.

Sadly, `fetch_extract_and_read()` does not exist as such, but as a combination of objects.

Once you have the full URL, fetching actually takes place through `conda.core.subdir_data.SubdirData`
objects. This object implements caching, authentication, proxies and other things that complicate
the simple idea of "just download the file please". Most of the logic is in `SubdirData._load()`,
which ends up calling `conda.core.subdir_data.fetch_repodata_remote_request()` to process the
request. Finally, `SubdirData._process_raw_repodata_str()` does the parsing and loading.

Internally, the `SubdirData` stores all the package metadata as a list of `PackageRecord` objects.
Its main usage is via `.query()` (one result at a time) or `.query_all()` (all possible matches).
These `.query*` methods accept spec strings (e.g. `numpy =1.14`), `MatchSpec` and `PackageRecord`
instances. Alternatively, if you want _all_ records with no queries, use `SubdirData.iter_records()`.

### Channel priorities

`context.channels` returns an `IndexedSet` of `Channel` objects; essentially a list of unique items.
The different channels in this list can have overlapping or even conflicting information for the same
package name. For example, `defaults` and `conda-forge` will for sure contain packages that fullfil
the `conda install numpy` request. Which one is chosen by `conda` in this case? It depends on the
`context.channel_priority` setting: From the help message:

> Accepts values of 'strict', 'flexible', and 'disabled'. The default value
> is 'flexible'. With strict channel priority, packages in lower priority channels
> are not considered if a package with the same name appears in a higher
> priority channel. With flexible channel priority, the solver may reach into
> lower priority channels to fulfill dependencies, rather than raising an
> unsatisfiable error. With channel priority disabled, package version takes
> precedence, and the configured priority of channels is used only to break ties.

In practice, `channel_priority=strict` is often the recommended setting for most users. It's faster
to solve and causes less problems down the line.

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
