# Type hinting

`conda` is an old project that was created when Python type hinting didn't exist yet. As a result, many parts of its codebase are not annotated yet. That said, we strive to progressively improve the type annotations coverage with each contribution. In this page we summarise the guiding principles that you should apply when adding type annotations in your contributions.

## Be abstract on inputs and concrete on outputs

The main idea is to follow the spirit of [Postel's law](https://en.wikipedia.org/wiki/Robustness_principle), but for types: input parameters should be type hinted as abstract as possible, while the return value should use the most concrete type hint available. For example, for a function that takes a string or a list of strings, and always returns a list of strings, we could do this:

```python
def ensure_list(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    return list(value)
```

However, the input type hint `list[str]` is unnecessarily restrictive. The function would probably accept any iterable just fine:

```python
from collections.abc import Iterable


def ensure_list(value: str | Iterable[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    return list(value)
```

Note how we the return type hint is still `list[str]`. Using `Iterable[str]` is not necessarily wrong, but we are being too forgiving there: we do know we always return a `list`, so why not provide that information.

Do explore the different abstract classes in [`collections.abc`](https://docs.python.org/3/library/collections.abc.html) to avoid having to create unnecessarily restrictive hints. For example, if you want to accept lists but not tuples, you might be tempted to use simply `list[...]`, but it would be even better to accept `MutableSequence[...]` for any objects implementing the same interface.

## Prefer modern typing options

Basically, use `from __future__ import annotations` in your modules and follow the linter rules. If you notice outdated type hints (e.g. using `Union[str, int]` instead of `str | int`) update them!

This particularly includes using the `typing.TYPE_CHECKING` boolean. If you are only importing a symbol for a type hint, it should be in that block.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
```

## Annotate all parameters and return types

Partial annotations are better than nothing, but let's strive for a full signature. This includes the return type hint. If there's no return value, that actually means we are returning `None`.

```python
# Wrong
def save_to_file(text: str, path: str):
    Path(path).write_text(text)


# OK
def save_to_file(text: str, path: str | Path) -> None:
    Path(path).write_text(text)
```

## Consider using multiple signatures

If the type hints are getting too complex (too many unions, many different return type hints), it may be time to consider whether you want to split the types in different signatures with `typing.overload` decorator. `conda.plugins.manager.CondaPluginManager.get_hook_results` is a good example for this use case.

## Custom type hints

`conda` ships with some custom types for type hinting. They are spread around the codebase so sometimes they are not easy to find. This is a summary:

- `conda.common.path.PathType`: Use it for values that represent file paths.
- `conda.common.path.PathTypes`: Use it for an iterable of `PathType` values.
