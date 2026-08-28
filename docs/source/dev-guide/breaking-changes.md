[cep8]: https://github.com/conda/ceps/blob/main/cep-0008.md
[cep9]: https://github.com/conda/ceps/blob/main/cep-0009.md

# Breaking changes

While conda strives towards providing a highly stable software and package management experience,
sometimes the introduction of breaking changes cannot be avoided.
For example, we may need to change a configuration default, update the solver,
or remove/change a CLI subcommand or flag. While these changes are usually few and far between,
it's important that we define the appropriate procedure to follow for our maintainers.
Additionally, [CEP 9][cep9] defines the deprecation schedule
for public API and behavior *removals*, but it does not by itself say how to plan, announce,
and ship a user-visible breaking change that isn't a symbol removal. This page describes the
process we use for that, building on CEP 9's schedule and [CEP 8][cep8]'s release cadence.

Read this together with {doc}`Deprecations <deprecations>` (the warning mechanics in code) and
{doc}`Releasing <releasing>` (how a release actually gets cut).

## Change categories

**Config default changes and removals**
: The setting itself stays supported; only its *implicit* default value changes (for example,
  flipping `add_pip_as_python_dependency` from `true` to `false`), or the setting is removed
  outright. Users who already set the value explicitly should see no behavior change.

**Default solver (or other high-impact default) changes**
: Swapping which plugin or implementation runs when the user hasn't chosen one, such as the
  23.10.0 switch to `conda-libmamba-solver`. These tend to have the widest blast radius and are
  the most likely candidates for a dedicated special release (see below).

**CLI subcommand or command option removals and behavior changes**
: Removing a subcommand, removing or renaming a flag, or changing what an existing invocation
  does — not just deprecating the Python API that backs it.

Every category follows the same rollout tools in [Communication and rollout](#communication-and-rollout);
they differ mainly in *how* conda warns users ahead of time.

## Relation to CEP 9

[CEP 9][cep9] and {doc}`Deprecations <deprecations>` give us the schedule (pending deprecation →
deprecation → removal) and the tooling (`deprecated`, `deprecated.argument`, `deprecated.action`,
`deprecated.constant`, `deprecated.module`, `deprecated.topic`) for deprecating a **symbol**.

CEP 9 alone is not enough when:

- The change is a **default value**, not a symbol. There is no function or argument to decorate
  with `@deprecated(...)`; instead, warn with `deprecated.topic(...)` at the point where conda
  falls back to the implicit default — and only when the user hasn't set the value explicitly.
- The change needs **rollout coordination** beyond a warning: a release-notes announcement, a
  blog post, installer coordination, or a dedicated release. None of that is covered by CEP 9;
  it's the subject of this page.
- The behavior lives partly **outside conda's code**, e.g. an installer-level change (like
  protected base environments) that ships through Miniconda/Miniforge rather than through a
  `PendingDeprecationWarning`.

If a change *is* a straightforward public symbol or behavior removal, use CEP 9's schedule and
`conda.deprecations` as documented in {doc}`Deprecations <deprecations>` and stop there — this
page only adds process for changes that need broader communication.

## Communication and rollout

Not every change needs every one of these; use judgment based on blast radius.

**Warn on the CLI when practical**
: If conda can detect that a user is relying on the soon-to-change default, emit a warning with
  `deprecated.topic(...)` (see the Topics section of {doc}`Deprecations <deprecations>`). Only
  warn when the behavior was *not* explicitly requested — never warn a user who set
  `solver: classic` or `add_pip_as_python_dependency: false` explicitly. Skip the warning
  entirely for settings that are a plain user opt-in/opt-out with no implicit default to migrate
  away from.

**Announce in the *previous* release's notes**
: Add a "Special announcement" section (see the 23.9.0 example below) or a clearly labeled
  `releases/news/` entry describing what will change and when, in the release *before* the one
  that ships the change. That gives users at least one release's notice in the changelog itself.

**Publish a [conda.org](https://conda.org) blog post for major changes**
: For changes with a wide blast radius (default solver, protected base, etc.), a blog post
  reaches users who don't read `CHANGELOG.md`. Link it from the release notes. For extra
  impact, you can link directly to that blog post with an [announcement banner](https://pydata-sphinx-theme.readthedocs.io/en/stable/user_guide/announcements.html).

**Prefer a dedicated special release on an even month for the highest-impact default flips**
: Deprecation releases land in March and September ([CEP 9][cep9]). Shipping a high-impact
  default flip in its own release on an even month keeps it out of deprecation-heavy releases,
  makes it easy to find in the changelog, and makes it easy to revert if needed. This is what we
  did for the libmamba solver switch in 23.10.0.

**Provide a migration and opt-out path**
: Document the config setting, CLI flag, or environment variable that restores the old behavior,
  and keep it working for at least one full deprecation cycle. Repeat this guidance in both the
  docs and the release notes announcing the change.

**Consider a beta installer for installer-coupled behavior**
: When the behavior depends on how Miniconda/Miniforge are built (for example, protected base
  environments), ship a beta installer build before the change reaches the general population,
  so downstream tooling can be tested against it first.

## Previous examples

### Default solver switch: `conda-libmamba-solver` (23.9.0 → 23.10.0)

- **23.9.0** shipped a "Special announcement" in the release notes stating the intent to switch,
  the opt-out flags (`--solver=classic`, `CONDA_SOLVER=classic`,
  `conda config --set solver classic`), and a link to the
  [rollout blog post](https://conda.org/blog/2023-07-05-conda-libmamba-solver-rollout).
- **23.10.0** was dedicated to the switch itself: `solver: libmamba` became the new default
  ([#12984](https://github.com/conda/conda/issues/12984)), and the release notes restated the same opt-out paths.

### Config default removal: implicit `defaults` channel (24.9.0 → 25.9.0)

- **24.9.0** marked the implicit `defaults` multichannel as pending deprecation, warned on the
  CLI only when the user hadn't configured `channels` explicitly, and documented the opt-back-in
  path (`conda config --add channels defaults`). ([#14178](https://github.com/conda/conda/issues/14178)
  via [#14227](https://github.com/conda/conda/pull/14227))
- **25.3.0** postponed the removal from the originally announced 25.3 to 25.9 in response to
  feedback — the schedule can slip without abandoning the process. ([#14178](https://github.com/conda/conda/issues/14178)
  via [#14662](https://github.com/conda/conda/issues/14662))
- **25.9.0** removed the implicit behavior. ([#15196](https://github.com/conda/conda/issues/14178))

This is the closer precedent for a config-default change that didn't need a dedicated release:
CLI warnings plus release-note announcements carried the communication load across releases.

## See also

- [CEP 8][cep8] — release cadence and versioning.
- [CEP 9][cep9] — deprecation schedule for public API/behavior removals.
- {doc}`Deprecations <deprecations>` — marking and removing APIs and behaviors in code.
- {doc}`Previews <previews>` — the opposite end of the lifecycle: opt-in experimental features.
- {doc}`Releasing <releasing>` — how a release, special or otherwise, actually gets cut.
- [#16404](https://github.com/conda/conda/issues/16404) — an in-progress example applying this
  process to the `add_pip_as_python_dependency` default.
