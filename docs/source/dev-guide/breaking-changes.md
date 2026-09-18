[cep8]: https://github.com/conda/ceps/blob/main/cep-0008.md
[cep9]: https://github.com/conda/ceps/blob/main/cep-0009.md

# Breaking changes

While conda strives towards providing a highly stable package manager experience,
sometimes the introduction of breaking changes cannot be avoided.
For example, we may need to change a configuration default, update the solver,
or remove/change a CLI subcommand or flag. While these changes are usually few and far between,
it's important that we define the appropriate procedure to follow for our maintainers.
This page applies [CEP 9][cep9]'s deprecation schedule to changes that break existing
supported workflows, including changes to implicit defaults. It adds communication and
rollout steps without shortening the notice period. [CEP 8][cep8] deliberately allows for
users who update every three or four months, rather than installing every release.

Read this together with {doc}`Deprecations <deprecations>` (the warning mechanics in code) and
{doc}`Releasing <releasing>` (how a release actually gets cut).

## Change categories

**Config default changes and removals**
: A default change keeps the setting supported but changes its *implicit* value (for example,
  flipping `add_pip_as_python_dependency` from `true` to `false`). Users who already set the
  value explicitly should see no behavior change. Removing the setting itself is a separate
  deprecation and must account for those explicit settings too.

**Default solver (or other high-impact default) changes**
: Swapping which plugin or implementation runs when the user hasn't chosen one, such as the
  23.10.0 switch to `conda-libmamba-solver`. These tend to have the widest blast radius and are
  the most likely candidates for a dedicated special release (see below).

**CLI subcommand or command option removals and behavior changes**
: Removing a subcommand, removing or renaming a flag, or changing what an existing invocation
  does — not just deprecating the Python API that backs it.

Every category follows the same notice requirements in
[Communication and rollout](#communication-and-rollout). They differ mainly in how conda
warns users ahead of time.

## Relation to CEP 9

If a change requires users to modify an existing supported command, configuration, or
workflow to keep it working, follow [CEP 9][cep9]'s pending, deprecated, and removal schedule.
Keeping the old behavior available through an explicit setting does not shorten that
schedule. For example, requiring users to request `pip` explicitly changes workflows that
previously installed Python and then ran `python -m pip`.

New opt-in features and implementation changes that preserve supported behavior do not
need a deprecation period merely because they introduce a setting or change internals.

Start the pending period in the release that first ships the notice and migration guidance,
not when an issue is opened or a pull request merges. Keep the old behavior through at least
two regular releases before active deprecation in the next March or September release.
Change the behavior no earlier than the following deprecation release. Optional and hotfix
releases do not count toward the required regular releases.

The pending period is also time for users to raise concerns. Link to a public tracking issue,
keep the dates provisional during this period, and resolve objections before confirming the
change. Follow CEP 9's dispute process if maintainers cannot reach agreement.

For example, a notice first shipped in 26.9 can become an active deprecation in 27.3 and
change the default in 27.9, provided the required regular releases have shipped. If the
notice or those releases are delayed, move the later stages to the next eligible releases.

Use the tools described in {doc}`Deprecations <deprecations>` for warning mechanics. A
default change can use `deprecated.topic(...)` where conda falls back to the implicit value.
For installer-level changes, provide the notice through the installer and its release notes.
The choice of warning mechanism does not change the notice period.

## Communication and rollout

Every breaking change needs the notice period, release notes, and migration guidance below.
Add CLI notices, blog posts, and installer previews as appropriate for the affected users.

**Warn on the CLI when practical**
: If conda can detect that an operation relies on the affected behavior, show a notice during
  normal CLI use starting in the pending release. During pending deprecation, describe the
  change as proposed and link to the discussion. Include the earliest target release and
  migration steps in the notice. A normally hidden `PendingDeprecationWarning` alone is not
  sufficient user-facing notice. Respect quiet and machine-readable output modes.

  For a default change, do not warn when the user explicitly configured a value that remains
  supported or explicitly requested the behavior, such as including `pip` in the package
  specs. Removing an explicit setting later requires a separate deprecation.

**Announce at the start of the notice period and repeat the reminder**
: Add a "Special announcement" section or a clearly labeled `releases/news/` entry in the
  first pending release. Describe the affected behavior, proposed dates, migration steps,
  and where users can raise concerns. Repeat the reminder in intervening release notes,
  including the release immediately before the change. That last announcement is a reminder,
  not the start of the notice period.

**Publish a [conda.org](https://conda.org) blog post for major changes**
: For changes with a wide blast radius (default solver, protected base, etc.), a blog post
  reaches users who don't read `CHANGELOG.md`. Link it from the release notes. For extra
  impact, you can link directly to that blog post with an [announcement banner](https://pydata-sphinx-theme.readthedocs.io/en/stable/user_guide/announcements.html).

**A dedicated release may delay the change, not bring it forward**
: A high-impact default change may ship in a dedicated even-month release after its notice
  period is complete. For example, a change eligible for 27.9 may move to 27.10, not 26.10.
  Record the later target in the notices and release notes. A dedicated release makes the
  change easier to identify and revert, but does not replace time for users to prepare.

**Provide a migration and opt-out path**
: Document the config setting, CLI flag, or environment variable that restores the old behavior.
  Keep it working for at least one full deprecation cycle after the default changes. Removing
  that opt-back-in requires its own CEP 9 deprecation process. Repeat the migration guidance
  in the docs and release notes.

**Consider a beta installer for installer-coupled behavior**
: When the behavior depends on how Miniconda/Miniforge are built (for example, protected base
  environments), ship a beta installer build before the change reaches the general population,
  so downstream tooling can be tested against it first.

## Previous examples

### Default solver switch: `conda-libmamba-solver` (2023 rollout)

- **July 2023**: the [rollout plan](https://conda.org/blog/2023-07-05-conda-libmamba-solver-rollout)
  publicly announced the intended switch, with plans to include the plugin in installers
  while keeping classic as the default and asking users to try it before the switch.

- **23.9.0** shipped a "Special announcement" in the release notes stating the intent to switch,
  the opt-out flags (`--solver=classic`, `CONDA_SOLVER=classic`,
  `conda config --set solver classic`), and a link to the
  [rollout blog post](https://conda.org/blog/2023-07-05-conda-libmamba-solver-rollout).
- **23.10.0** was dedicated to the switch itself: `solver: libmamba` became the new default
  ([#12984](https://github.com/conda/conda/issues/12984)), and the release notes restated the same opt-out paths.

This example shows release coordination, not a minimum notice period for future changes.
The 23.9 announcement was part of an existing rollout, not its first public notice.

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
