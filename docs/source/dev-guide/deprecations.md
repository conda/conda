[cep9]: https://github.com/conda-incubator/ceps/blob/main/cep-9.md

# Deprecations

Conda abides by the Deprecation Schedule defined in [CEP-9][cep9]. To help make deprecations as much of a no-brainer as possible we provide several helper decorators and functions to facilitate the correct deprecation process.

## Functions, Methods, and Properties

The simplest use case is for deprecating any function, method, or property:

```python
from conda.deprecations import deprecated


@deprecated("23.9", "24.3")
def foo():
    ...
```

As a minimum we must always specify two versions:

1. the future deprecation release in which the function, method, or property will be marked as deprecated; prior to that the feature will show up as pending deprecation (which we treat as a commenting period), and
2. the subsequent deprecation release in which the function, method, or property will be removed from the code base.

Additionally, you may provide an addendum to inform the user what they should do instead:

```python
from conda.deprecations import deprecated


@deprecated("23.9", "24.3", addendum="Use `bar` instead.")
def foo():
    ...
```

## Keyword Arguments

!!! warning
    Deprecating or renaming a positional argument is unnecessarily complicated and so it isn't supported. It is recommended to either (1) devise a custom way of detecting usage of a deprecated positional argument (e.g., type checking) and using the `conda.deprecations.deprecated.topic` function (see [Topics](#topics)) or (2) deprecate the function/method itself and defining a new function/method without the deprecated argument.

Similarly to deprecating a function or method it is common to deprecate a keyword argument or to rename the keyword argument:

```python
from conda.deprecations import deprecated


def old_foo(is_true=True):
    ...


@deprecated.argument("23.9", "24.3", "is_true")
def foo():
    ...


@deprecated.argument("23.9", "24.3", "is_true", rename="enabled")
def foo(enabled=True):
    ...
```

## Module

## Constant

## Topics
