# Type hinting

`conda` is an old project that was created when Python type hinting didn't exist yet. As a result, many parts of its codebase are not annotated. That said, we strive to progressively improve the type annotation coverage with each contribution. On this page, we summarize the guiding principles that you should apply when adding type annotations in your contributions.

## Main principles

We adhere to the [Typing Best Practices](https://typing.python.org/en/latest/reference/best_practices.html) recommended by the official Python documentation. Some additional tips can be found in [Google's Python Guide: Type Annotations](https://google.github.io/styleguide/pyguide.html#s3.19-type-annotations) (ignore the formatting concerns, those are dealt with automatically by our pre-commit hooks).

From those tips, we emphasize:

- Be abstract on inputs and concrete on outputs (tip: explore the different abstract classes in [`collections.abc`](https://docs.python.org/3/library/collections.abc.html)).
- Use `from __future__ import annotations` in your modules to opt-in for the most recent type hinting capabilities (e.g. deferred evaluation).
- If there's no return value, that actually means we are returning `None`. Annotate it!

## Consider using multiple signatures

If your type hints are getting too complex (too many unions, many different return type hints), it may be time to consider whether you want to split the types in different signatures with `typing.overload` decorator. `conda.plugins.manager.CondaPluginManager.get_hook_results` is a good example for this use case.

## Custom type hints

`conda` ships with some custom types for type hinting. They are spread around the codebase, so sometimes they are not easy to find. This is a summary:

- `conda.common.path.PathType`: Use it for values that represent file paths.
- `conda.common.path.PathTypes`: Use it for an iterable of `PathType` values.

## Local development

### Linters

We use `ruff` to lint and format our codebase. We have selected a few type hinting related rules, but we have not added [`ANN`](https://docs.astral.sh/ruff/rules/#flake8-annotations-ann) yet. That said, you can enable it temporarily in your `pyproject.toml` while developing locally.

### Type hinting coverage

The `linux-typing` job in `tests.yml` runs MyPy and uploads the [reports to codecov under the label `MyPy`](https://app.codecov.io/github/conda/conda?flags%5B0%5D=MyPy). Its only purpose is to track type hinting coverage, not to report type hinting errors (yet).

In this [codecov.io webapp report](https://app.codecov.io/github/conda/conda/tree/main/conda?flags%5B0%5D=MyPy), you can find the coverage for every Python file in the codebase.
