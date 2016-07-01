# Contributing to conda-env

So you wanna contribute?!  Awesome! :+1:

There are a couple of ways you can contribute to the development.  Not all of
which require you do any coding.


## Reporting Issues

We try are best to make sure there aren't issues with all of code we release,
but occasionally bugs (:bug:) make it through and are released.  Here's a
checklist of things to do:

* [ ] Make sure you're on the latest version of `conda-env`.  You can do that
  by running `conda update conda-env`.
* [ ] If you're adventurous, you can try running the latest development version
  by running `conda update --channel conda/c/dev conda-env` (you can also
  use `-c` as the short parameter).

If updating `conda-env` doesn't work for you, the next thing to d
[open a report][].  Here are a few things to make sure you include to help us
out the most:

* [ ] Explain what you expect to happen and what actually happened.
* [ ] Add the steps you used to reproduce the error.
* [ ] Include the command you ran and *all* of the output.  The error message is
  useful, but often information that's displayed before that can point us in
  the right direction.
* [ ] Include all of the output from `conda info --all` (or `conda info -a`).
* [ ] Include the output from `conda list conda` (note: you need to include
  `--name root` if you have an environment activated).

The last three outputs can be posted in a [gist][] and included in the issue as
a link.


## Run development versions

We automatically build new versions of `conda-env` using [binstar build][].
Every commit that hits our [develop branch][] is automatically built and added
to our [conda/c/dev][] channel.  You can add that channels to your conda config
and you will always be on the latest versions of conda-env.  

> **Warning**: This is meant for people who are interested in actively helping
> further development of conda-env.  You should only use it if you're ok with
> conda-env occasionally being broken while we work out issues before a release.

```bash
conda config --add channels conda/c/dev
```

## Contribute Code

The easiest thing to do is contribute a feature or fix a bug that you've found.
If you want to contribute but don't know where to start, check out our
(hopefully) small list of [open bugs][].  If you want to take a stab at adding
something, check out the list of [open enhancement requests][].

Once you know what you're going to add, there's a few things you can do to help
us figure out how to process your code:

* [Create a fork](https://github.com/conda/conda-env/fork)
* Create a branch with your change off of `develop`.  Follow these naming
  conventions for naming your branches:
  * `feature/{{ feature name }}` <-- new features
  * `fix/{{ issue number or general bug description }}` <-- fixes to the code
  * `refactor/{{ refactor name / description }}` <-- general cleanup /
      refactoring
* Commit your changes to your branch.  Changes with extensive unit tests are
  given priority because they simplify the process of verifying the code.
* Open a pull request against the `develop` branch
* :tada: profit!

There's a lot happening in conda-land.  We might not always get right back to
you and your PR, but we'll try to do it as quickly as possible.  If you haven't
heard anything after a few days to a week, please comment again to make sure
notices are sent back out.


## Coding Guidelines

The rest of this document is aimed at people developing and releasing conda-env.


### Coding Style

* Please run all of your code through [flake8][] (yes, it's more strict than
  straight [pep8][], but it helps ensure a consistent visual style for our
  code).
* Please include tests for all new code and bugfixes.  The tests are run using
  [pytest][] so you can use things like [parameterized tests][] and such.
* Please [mark any tests][] that are slow with the `@pytest.mark.slow`
  decorator so they can be skipped when needed.


### Releasing conda-env

conda-env follows [SemVer][] with one specific change: pre-release versions are
denoted without using a hyphen.  For example, a development version of conda-env
might be `2.1alpha.0`.  Anything released with the `alpha` must be treated as
not-final code.

* The `develop` branch should always have a version number that is +1 minor
  version ahead of what is in `master`.  For example, if the latest code in
  `master` is `v2.0.2`, the `develop` branch should be `v2.1alpha.0`.


#### Merging Feature Releases to `master`

If you're ready to release, open a PR to ensure that `develop` has everything
that it needs for this release, including any **updates to change logs** and such.
Do not merge `conda-env` directly via GitHub's interface.  Instead, follow
these steps from your working tree (note: this assumes you have
github.com/conda/conda-env.git setup as the remote `conda`):

* `git fetch conda-env`
* `git checkout master`
* `git merge --no-ff --no-commit conda-env/develop`
* Modify the `setup.py` and `conda.recipe/meta.yaml` to remove the `alpha` from
  the minor version.
* `git commit` the changes.  Ensure that the subject line includes the version
  number at the end of the message.  You may also wish to include a descriptive
  sentence explaining the main feature(s) of the release.
* `git tag vX.Y.Z`
* `git push conda-env master --tags`
* After binstar build has successfully built the new version, make sure that all
  builds are added to the `main` channel of conda-env.

> Author's Note: It would be great to automate this entirely into a tool that
> would build a release for you!


#### Handling Bugfix Releases

You should create a new branch called `vX.Y.Z-prep` from the tag and increment
the bugfix version number (`Z` in this example) by one and add `alpha`.  For
example, if the latest release is `v2.0.2`, you would create a branch called
`v2.0.3alpha` and the first commit should be the changes to `setup.py` and
`conda.recipe/meta.yaml`.

Please open a pull request for this fix, but do not merge via GitHub.  Instead,
follow the outline above to handle the bugfix release.  Once merged, make sure
to merge `master` into `develop` and push that branch as well so the bugfix is
included in future versions.


[binstar build]: http://docs.anaconda.org/build_cli.html
[conda/c/dev]: https://conda.anaconda.org/conda/c/dev
[develop branch]: https://github.com/conda/conda-env/tree/develop
[flake8]: http://flake8.readthedocs.org/
[gist]: https://gist.github.com/
[mark any tests]: http://pytest.org/latest/example/markers.html
[open a report]: https://github.com/conda/conda-env/issues/new
[open bugs]: https://github.com/conda/conda-env/issues?q=is%3Aopen+is%3Aissue+label%3Abug
[open enhancement requests]: https://github.com/conda/conda-env/issues?q=is%3Aopen+is%3Aissue+label%3Aenhancement
[parameterized tests]: http://pytest.org/latest/parametrize.html#parametrize
[pep8]: https://www.python.org/dev/peps/pep-0008/
[pytest]: http://pytest.org/latest/
[SemVer]: http://semver.org/
