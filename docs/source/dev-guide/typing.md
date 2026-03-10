# Type hinting

`conda` is an old project that was created when Python type hinting didn't exist yet. As a result, many parts of its codebase are not annotated yet. That said, we strive to progressively improve the type annotations coverage with each contribution. In this page we summarise the guiding principles that you should apply when adding type annotations in your contributions.

## Main principles

We subscribe to the [Typing Best Practices](https://typing.python.org/en/latest/reference/best_practices.html) recommended by the official Python documentation. Some additional tips can be found in [Google's Python Guide: Type Annotations](https://google.github.io/styleguide/pyguide.html#s3.19-type-annotations) (ignore the formatting concerns, those are dealt automatically by the pre-commit hooks).

From those tips, we emphasize:

- Be abstract on inputs and concrete on outputs. Tip: explore the different abstract classes in [`collections.abc`](https://docs.python.org/3/library/collections.abc.html).
- Use `from __future__ import annotations` in your modules to opt-in for the most recent type hinting capabilities (e.g. deferred evaluation).
- If there's no return value, that actually means we are returning `None`. Annotate it!

## Consider using multiple signatures

If the type hints are getting too complex (too many unions, many different return type hints), it may be time to consider whether you want to split the types in different signatures with `typing.overload` decorator. `conda.plugins.manager.CondaPluginManager.get_hook_results` is a good example for this use case.

## Custom type hints

`conda` ships with some custom types for type hinting. They are spread around the codebase so sometimes they are not easy to find. This is a summary:

- `conda.common.path.PathType`: Use it for values that represent file paths.
- `conda.common.path.PathTypes`: Use it for an iterable of `PathType` values.
