[cep9]: https://github.com/conda-incubator/ceps/blob/main/cep-9.md

# Deprecations

Conda abides by the Deprecation Schedule defined in [CEP-9][cep9]. To help make deprecations as much of a no-brainer as possible we provide several helper decorators and functions to facilitate the correct deprecation process.

## Functions, Methods, and Properties

The simplest use case is for deprecating any function, method, or property:

```{code-block} python
:caption: Example file, `foo.py`.
from conda.deprecations import deprecated


@deprecated("23.9", "24.3")
def bar():
    ...
```

```{code-block} pycon
:caption: Example invocation.
>>> import foo
>>> foo.bar()
<stdin>:1: PendingDeprecationWarning: foo.bar is pending deprecation and will be removed in 24.3.
```

As a minimum we must always specify two versions:

1. the future deprecation release in which the function, method, or property will be marked as deprecated; prior to that the feature will show up as pending deprecation (which we treat as a commenting period), and
2. the subsequent deprecation release in which the function, method, or property will be removed from the code base.

Additionally, you may provide an addendum to inform the user what they should do instead:

```{code-block} python
:caption: Example file, `foo.py`.
from conda.deprecations import deprecated


@deprecated("23.9", "24.3", addendum="Use `qux` instead.")
def bar():
    ...
```

```{code-block} pycon
:caption: Example invocation.
>>> import foo
>>> foo.bar()
<stdin>:1: PendingDeprecationWarning: foo.bar is pending deprecation and will be removed in 24.3. Use `qux` instead.
```

## Keyword Arguments

:::{warning}
Deprecating or renaming a positional argument is unnecessarily complicated and so it isn't supported. It is recommended to either (1) devise a custom way of detecting usage of a deprecated positional argument (e.g., type checking) and using the `conda.deprecations.deprecated.topic` function (see [Topics](#topics)) or (2) deprecate the function/method itself and defining a new function/method without the deprecated argument.
:::

Similarly to deprecating a function or method it is common to deprecate a keyword argument:

```{code-block} python
:caption: Example file, `foo.py`.
from conda.deprecations import deprecated


# prior implementation
# def bar(is_true=True):
#     ...


@deprecated.argument("23.9", "24.3", "is_true")
def bar():
    ...
```

```{code-block} pycon
:caption: Example invocation.
>>> import foo
>>> foo.bar(is_true=True)
<stdin>:1: PendingDeprecationWarning: foo.bar(is_true) is pending deprecation and will be removed in 24.3.
```

Or to rename the keyword argument:

```{code-block} python
:caption: Example file, `foo.py`.
from conda.deprecations import deprecated


# prior implementation
# def bar(is_true=True):
#     ...


@deprecated.argument("23.9", "24.3", "is_true", rename="enabled")
def bar(enabled=True):
    ...
```

```{code-block} pycon
:caption: Example invocation.
>>> import foo
>>> foo.bar(is_true=True)
<stdin>:1: PendingDeprecationWarning: foo.bar(is_true) is pending deprecation and will be removed in 24.3. Use 'enabled' instead.
```

## Constant

We also offer a way to deprecate global variables or constants:

```{code-block} python
:caption: Example file, `foo.py`.
from conda.deprecations import deprecated

deprecated.constant("23.9", "24.3", "ULTIMATE_CONSTANT", 42)
```

```{code-block} pycon
:caption: Example invocation.
>>> import foo
>>> foo.ULTIMATE_CONSTANT
<stdin>:1: PendingDeprecationWarning: foo.ULTIMATE_CONSTANT is pending deprecation and will be removed in 24.3.
```

:::{note}
Constants deprecation relies on the module's `__getattr__` introduced in [PEP-562](https://peps.python.org/pep-0562/).
:::

## Module

Entire modules can be also be deprecated:

```{code-block} python
:caption: Example file, `foo.py`.
from conda.deprecations import deprecated

deprecated.module("23.9", "24.3")
```

```{code-block} pycon
:caption: Example invocation.
>>> import foo
<stdin>:1: PendingDeprecationWarning: foo is pending deprecation and will be removed in 24.3.
```

## Topics

Finally, there are a multitude of other ways in which code may be run that also needs to be deprecated. To this end we offer a general purpose deprecation function:

```{code-block} python
:caption: Example file, `foo.py`.
from conda.deprecations import deprecated

def bar(...):
    # some logic

    if ...:
        deprecated.topic("23.9", "24.3", topic="The <TOPIC>")

    # some more logic
```

```{code-block} pycon
:caption: Example invocation.
>>> import foo
>>> foo.bar(...)
<stdin>:1: PendingDeprecationWarning: The <TOPIC> is pending deprecation and will be removed in 24.3.
```
