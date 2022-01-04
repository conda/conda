(deep_dive_solvers)=

# Deep dive: solvers

The guide {ref}`deep_dive_install` didn't go into details of the solver black box. It did mention
the high-level `Solver` API and how `conda` expects a Transaction out of it, but we never got to
learn what happens _inside_ the solver itself. We only covered these three steps:

> The details are complicated, but in essence, the solver will:
>
> 1. Express the requested packages, command line options and prefix state as `MatchSpec` objects
> 2. Query the index for the best possible match that satisfy those constrains
> 3. Return a list of `PackageRecord` objects.


How do we transform the prefix state and configurations into a list of `MatchSpec` objects? How
are those turned into a list of `PackageRecord` objects? Where are those `PackageRecord`
objects coming from? We are going to cover these aspects in detail here.

## `MatchSpec` vs `PackageRecord`

First, let's define what each object does:

* [`PackageRecord`][conda.models.records:PackageRecord] objects represent a concrete package
  tarball and its contents. They follow [specific naming conventions][conda_package_naming] and
  expose several fields. Inspect them directly in the
  [class code][conda.models.records:PackageRecord].
* [`MatchSpec`][conda.models.match_spec:MatchSpec] objects are essentially a query language to
  find `PackageRecord` objects. Internally, `conda` will translate your command line requests,
  like `numpy>=1.19`, `python=3.*` or `pytorch=1.8.*=*cuda*`, into instances of this class.
  This query language has its own syntax and rules, detailed [here][conda_package_spec]. The
  most important fields of a `MatchSpec` object are:
  * `name`: the name of the package (e.g. `pytorch`), always expected.
  * `version`: the version constrains (e.g. `1.8.*`), can be empty but if `build` is set, set it to
    `*` to avoid issues with the `.conda_build_form()` method.
  * `build`: the build string constrains (e.g. `*cuda*`), can be empty.

```{tip} Create a MatchSpec from a PackageRecord

You can create a `MatchSpec` object from a `PackageRecord` instance using the `.to_match_spec()`
method. This will create a `MatchSpec` object with its fields set to exactly match the originating
`PackageRecord`.
```

Note that there are two `PackageRecord` subclasses with extra fields, so we need to distinguish
between three types, all of them useful:
* `PackageRecord`: A record as present in the index (channel).
* `PackageCacheRecord`: A record already extracted in the cache. Contains extra fields for the
  tarball path in disk and its extracted directory.
* `PrefixRecord`: A record installed in a prefix. Same as above, plus fields for the files that
  make the package and how they were linked in the prefix. It can also host information about which
  `MatchSpec` string resulted into this record being installed.

## Remote state: the index

So the solver takes `MatchSpec` objects, query the index for the best match and returns
`PackageRecord` objects. Perfect. What's the index? It's the result of aggregating the
requested conda channels in a single entity. For more information, check
{ref}`deep_dive_install_index`.

## Local state: the prefix and context

When you do `conda install numpy`, do you think the solver will just see something like
`specs=[MatchSpec("numpy")]`? Well, not that quick. The explicit instructions given by the user
are only one part of the request we will send to the solver. Other pieces of implicit state are
taken into account to build the final request. Namely, the state of your prefix. In total,
these are the ingredients of the solver request.

1. Packages already present in your environment, if you are not _creating_ a new one. This is
   exposed through the `conda.core.prefix_data.PrefixData` class, which provides an iterator method
   via `.iter_records()`. As we saw before, this yields `conda.models.records.PrefixRecord`
   objects, a `PackageRecord` subclass for installed records.
2. Past actions you have performed in that environment; the _History_. This is a journal of all the
   `conda install|update|remove` commands you have run in the past. In other words, the _specs_
   matched by those previous actions will receive extra protections in the solver.
3. Packages included in the _aggressive updates_ list. These packages are always included in any
   requests to make sure they stay up-to-date under all circumstances.
4. Packages pinned to a specific version, either via `pinned_packages` in your `.condarc` or defined
   in a `$PREFIX/conda-meta/pinned` file.
5. In new environments, packages included in the `create_default_packages` list. These specs are
   injected in each `conda create` command, so the solver will see them as explicitly requested
   by the user.
6. And, finally, the specs the user is asking for. Sometimes this is explicit (e.g.
   `conda install numpy`) and sometimes a bit implicit (e.g. `conda update --all` is telling the
   solver to add all installed packages to the update list).

All of those sources of information produce a number a of `MatchSpec` objects which are then
combined and modified in very specific ways depending on the command-line flags and their origin
(e.g. specs coming from the pinned packages won't be modified, unless the user asks for it
explicitly). This logic is intricate will be covered in the next sections.

## The solver logic



## Early exit tasks

WIP

## Compiling the full list of `MatchSpec` requests

WIP


## `MatchSpec` to SAT clauses

WIP

## Solving the SAT problem

WIP


Once the solver receives the list of specs it needs to resolve, we can consider it will do some
magic and, eventually, either:

* Succeed and return a list of `PackageRecord` objects: those entries in the index that match
  our request. More on this in the next section.
* Fail with an `UnsatisfiableError`. The details of this error are gathered through a rather
  expensive function that tries to recover _why_ the request is unsatisfiable. This is done in the
  [`build_conflict_map` function][conda.resolve:build_conflict_map].



## Back to `conda` packages... or not

WIP

```{admonition} Disabling unsatisfiable hints

Unsatisfiability reasons can be disabled through the `context` options, but unfortunately that
gets in the way of conda's iterative logic. It will shortcut any constrained attempts and prevent
the solver from trying less constrained specs. This is a part of the logic that should be improved.
```


<!-- Links -->
[conda_package_spec]: https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications
[conda_package_naming]: https://docs.conda.io/projects/conda-build/en/latest/concepts/package-naming-conv.html
[conda.models.records:PackageRecord]: https://github.com/conda/conda/blob/4.11.0/conda/models/records.py#L242
[conda.models.match_spec:MatchSpec]: https://github.com/conda/conda/blob/4.11.0/conda/models/match_spec.py#L73