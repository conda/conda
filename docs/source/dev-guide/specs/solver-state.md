```{admonition} Work in progress
This page of the documentation is not yet finished and only contains a draft of the content.
```

# Technical specification: solver state

:::{admonition} Note
:class: warning

This document is a technical specification, which might not be the best way to learn about
how the solver works. For that, refer to {doc}`../deep-dives/install` and
{doc}`../deep-dives/solvers`.
:::

The `Solver` API will pass a collection of `MatchSpec` objects (from now on, we will refer to
them as `specs`) to the underlying SAT solver. How this list is built from the prefix state
and context options is not a straightforward process, but an elaborate logic. This is better
understood if we examine the _ingredients_ that participate in the construction of `specs`. We
will label them like this:

These groups below will _not_ change during the solver attempts:

1. `requested`: `MatchSpec` objects the user is _explicitly_ asking for.
2. `installed`: Installed packages, expressed as `PrefixRecord` objects. Empty if the
   environment did not exist.
3. `history`: Specs asked in the past: the `History`. Empty if the environment did not exist.
4. `aggressive_updates`: Packages included in the _aggressive updates_ list. These packages are
   always included in any requests to make sure they stay up-to-date under all circumstances.
5. `pinned`: Packages pinned to a specific version, either via `pinned_packages` in your
   `.condarc` or defined in a `$PREFIX/conda-meta/pinned` file.
6. `virtual`: System properties exposed as virtual packages (e.g. `__glibc=2.17`). They can't
   really be installed or uninstalled, but they do participate in the solver by adding runtime
   constraints.
7. `do_not_remove`: A fixed list of packages that receive special treatment by the solver due
   to poor metadata in the early days of conda packaging. A legacy leftover.

This one group _does_ change during the solver lifetime:

8. `conflicting`: Specs that are suspected to be a conflict for the solver.

Also, two more sources that are not obvious at first. These are not labeled as a _source_, but they
do participate in the `specs` collection:

* In new environments, packages included in the `contex.create_default_packages` list. These
  `MatchSpec` objects are injected in each `conda create` command, so the solver will see them
  as explicitly requested by the user (`requested`).
* Specs added by command line modifiers. The specs here present aren't new (they are already in
  other categories), but they might end up in the `specs` list only when a flag is added. For
  example, `update --all` will add all the installed packages to the `specs` list, with no
  version constraint. Without this flag, the installed packages will still end up in the `specs`
  list, but with full constraints (`--freeze-installed` defaults for the first attempt) unless:
    * Frozen attempt failed.
    * `--update-specs` (or any other `UpdateModifier`) was passed, overriding `--freeze-installed`.

See? It gets involved. We will also use this vocabulary to help narrow down the type of change
being done:

Types of `spec` objects:

* `specs`: map of package name to its currently corresponding `MatchSpec` instance.
* `spec`: specific instance of a `MatchSpec` object.
* Exact or frozen `spec`: a `spec` where both the `version` and `build` fields are constrained
  with `==` operators (exact match).
* Fully constrained or tight `spec`: a `spec` where both `version` and `build` are populated,
  but not necessarily with equality operators. It can also be inequalities (`>`, `<`, etc.) and
  fuzzy matches (`*something*`).
* Version-only `spec`: a `spec` where _only_ the `version` field is populated. The `build`
  is not.
* Name-only, bare, or unconstrained `spec`: a `spec` with no `version` or `build ` fields. Just
  the name of the package.
* Targeted `spec`: a `spec` with the `target` field populated. Extracted from the comments in
  the solver logic:
    > `target` is a reference to the package currently existing in the environment. Setting
    > `target` instructs the solver to not disturb that package if it's not necessary. If the
    > spec.name is being modified by inclusion in `specs_to_add`, we don't set `target`, since we
    > *want* the solver to modify/update that package.
    >
    > TL;DR: when working with `MatchSpec` objects,
    >  - to minimize the version change, set `MatchSpec(name=name, target=prec.dist_str())`
    >  - to freeze the package, set all the components of `MatchSpec` individually
* if the `spec` object does not have an adjective, it should be assumed it's being added to the
  `specs` map unmodified, as it came from its origin.

Pools (collections of `PackageRecord` objects):
* Installed pool: The installed packages, grouped by name. Each group should only contain one record!
* Explicit pool: The full index, but reduced for the specs in `requested`.

The following sections will get dry and to the point. They will state what output to expect from
a given set of initial conditions. At least we'll try. Take into account that the `specs` list
is kept around across attempts! In other words, the `specs` list is only really empty in the first
attempt; if this fails, the subsequent attempts will only overwrite (update) the existing one. In
practice, this should only affect how constrained packages are. The names should be the same.

It will also depend on whether we are adding (`conda install|create|update`) or removing
(`conda remove`) packages. There's a common initialization part for both, but after that the
logic is separate.

<!--
I will first describe what we are doing step by step. Hopefully by writing this down we can
think of potential simplifications of the logic and its implementation.
-->

# Common initialization

> Note: This happens in `Solver._collect_all_metadata()`

This happens regardless of the type of command we are using (`install`, `update`, `create` or
`remove`).

1. Add specs from `history`, if any.
2. Add specs from `do_not_remove`, but only if:
    * There's no spec for that name in `specs` already, _and_
    * A package with that name is _not_ installed.
3. Add `virtual` packages as unconstrained `specs`.
4. Add all those installed packages, as unconstrained `specs`, that satisfy any of these conditions:
    * The history is empty (in that case, all installed packages are added)
    * The package name is part of `aggresive_updates`
    * The package was not installed by `conda`, but by pip or other PyPI tools instead.

<!--
This is getting simplified in the libmamba refactor, as the following. It should be equivalent:

If we have a history:
    * Add history specs
    * Add installed packages as unconstrained specs that satisfy any of these conditions:
        * Part of aggresive updates
        * Part of do_not_remove
        * Installed by pip
Else, we add _all_ installed packages as unconstrained specs.

Finally, add virtual packages as bare specs.
-->

```{admonition} Preparing the index
At this point, the populated `specs` and the `requested` specs are merged together. This temporary
collection is used to determine how to reduce the index.
```
# Processing specs for `conda install`

## Preparation

1. Generate the explicit pool for the requested specs (via `Resolve._get_package_pool()`).
2. Detect potential conflicts (via (`Resolve.get_conflicting_specs()`).

## Refine `specs` that match installed records

1. Check that each of `specs` match a single installed package or none! If there are two or more
   matches, it means that the environment is in bad shape and is basically broken. If the `spec`
   matches one installed package (let's call it _installed match_), we will modify the original
   `spec`.
2. We will turn the `spec` into an _exact_ (frozen) spec if:
    1. The installed match is unmanageable (installed by pip, virtual, etc.)
    2. There's no history, we are not in `--freeze-installed` mode, and:
        * The spec is not a potential conflict, _and_
        * The package name _cannot_ be found in the explicit pool index or, if it is, the
          installed match can be found in that explicit pool (to guarantee it will be found
          instead of creating one more conflict _just because_).
3. We relax the `spec` to a name-only `spec` if it's part of the aggressive updates list.
4. We turn it into a targeted `spec` if:
    1. The spec is in `history`. In that case, we take its _historic_ spec counterpart and set the
       target to the installed match version and build.
    2. None of the above conditions were met. In other words, we'll try our best to match the
       installed package if none of the above applies, but if we fail we'll stick to whatever was
       already present in the `specs`.

## Handle pinned specs

<!-- WIP -->

# Processing specs for `conda remove`

<!-- WIP -->
