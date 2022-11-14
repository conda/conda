(deep_dive_context)=

# `conda config` and context

The `context` object is central to many parts of the `conda` codebase. It serves as a centralized
repository of settings. You normally import the singleton and access its (many) attributes directly:

```python
from conda.base.context import context

context.quiet
# False
```

This singleton is initialized from a cascade of different possible sources. From lower to higher
precedence:

1. Default values hardcoded in the `Context` class. These are defined via class attributes.
2. Values defined in the configuration files (`.condarc`), which have their own
   {ref}`precedence <condarc_search_precedence>`.
3. Values set by the corresponding command line arguments, if any.
4. Values defined by their corresponding `CONDA_*` environment variables, if present.

The mechanism implementing this behavior is an elaborate object with several types of objects
involved.

## Anatomy of the `Context` class

`conda.base.context.Context` is an conda-specific subclass of the application-agnostic
`conda.common.configuration.Configuration` class. This class implements the precedence order
for the instantiation of each defined attribute, as well as the overall validation logic and help
message reporting. But that's it, it's merely a storage of `ParameterLoader` objects which, in
turn, instantiate the relevant `Parameter` subclasses in each attribute. Roughly:

```python
class MyConfiguration(Configuration):
    string_field = ParameterLoader(PrimitiveParameter("default", str))
    list_of_int_field = ParameterLoader(SequenceParameter([1, 2, 3], int))
    map_of_foat_values_field = ParameterLoader(MapParameter({"key": 1.0}, float))
```

When `MyConfiguration` is instantiated, those class attributes are populated by the `.raw_data`
dicionary that has been filled in with the values coming from the precedence chain stated
above. The `raw_data` dictionary contains `RawParameter` objects, subclassed to deal with the
specifics of their origin (YAML file, environment variable, command line flag). Each
`ParameterLoader` object will pass the `RawParameter` object to the `.load()` method of its relevant
`Parameter` subclass, which are designed to return their corresponding `LoadedParameter` object
counterpart.

It's a bit confusing, but the delegation happens like this:

1. The `Configuration` subclass parses the raw values of the possible origins and stores them as
   the relevant `RawParameter` objects, which can be:
   * `EnvRawParameter`: for those coming from an environment variable
   * `ArgParseRawParameter`: for those coming from a command line flag
   * `YamlRawParameter`: for those coming from a configuration file
   * `DefaultValueRawParameter`: for those coming from the default value given to `ParameterLoader`
2. Each `Configuration` attribute is a `ParameterLoader`, which implements the `property` protocol
   via `__get__`. This means that, upon attribute access (e.g. `MyConfiguration.string_field`),
   the `ParameterLoader` can execute the loading logic. This means finding potential type matches
   in the raw data, loading them as `LoadedParameter` objects and merging them with the adequate
   precedence order.

The merging policy depends on the `(Loaded)Parameter` subtype. Below is a list of available
subtypes:

* `PrimitiveParameter`: holds a single scalar value of type `str`, `int`, `float`, `complex`, `bool`
  or `NoneType`.
* `SequenceParameter`: holds an iterable (`list`) of other `Parameter` objects.
* `MapParameter`: holds a mapping (`dict`) of other `Parameter` objects.
* `ObjectParameter`: holds an object with attributes set to `Parameter` objects.

The main goal of the `Parameter` objects is to implement how to typify and turn the raw values into
their `Loaded` counterparts. These implement the validation routines and define how parameters for
the same key should be merged:

* `PrimitiveLoadedParameter`: value with highest precedence replaces the existing one.
* `SequenceLoadedParameter`: extends with no duplication, keeping precedence.
* `MapLoadedParameter`: cascading updates, highest precedence kept.
* `ObjectLoadedParameter`: same as `Map`.

After all of this, the `LoadedParameter` objects are _typified_: this is when type validation is
performed. If everything goes well, you obtain your values just fine. If not, the validation errors
are raised.

Take into account that the result is cached for faster subsequent access. This means that even
if you change the value of the environment variables responsible for a given setting, this won't be
reflected in the `context` object until you refresh it with `conda.base.context.reset_context()`.

```{admonition} Do not modify the Context object!

`ParameterLoader` does not implement the `__set__` method of the `property` protocol, so you
can freely override an attribute defined in a `Configuration` subclass. You might think that
this will redefine the value after passing through the validation machinery, but that's not true.
You will simply overwrite it entirely with the raw value and that's probably not what you want.

Instead, consider the `context` object immutable. If you need to change a setting at runtime, it is
probably _A Bad Idea_. The only situation where this is acceptable is during testing.
```

## Setting values in the different origins

There's some magic behind the possible origins for the settings values. How these are tied to the
final `Configuration` object might not be obvious at first. This is different for each
`RawParameter` subclass:

* `DefaultValueRawParameter`: Users will never see this one. It only wraps the default value passed
  to the `ParameterLoader` class. Safe to ignore.
* `YamlRawParameter`: This one takes a YAML file and parses it as a dictionary. The keys in this
  file must match the attribute names in the `Configuration` class exactly (or one of their
  aliases). Matching happens automatically once this is properly set up. How the values are parsed
  depends on the YAML Loader, set internally by `conda`.
* `EnvRawParameter`: Values coming from certain environment variables can make it to the
  `Configuration` instance, provided they are formatted as `<APP_NAME>_<PARAMETER_NAME>`, all
  uppercase. The app name is defined by the `Configuration` subclass. The parameter name is
  defined by the attribute name in the class, transformed to upper case. For example,
  `context.ignore_pinned` can be set with `CONDA_IGNORE_PINNED`. The value of the variable is parsed
  in different ways depending on the type:
    * `PrimitiveParameter` is the easy one. The environment variable string is parsed as the
      expected type. Booleans are a bit different since several strings are recognized as such, and
      in a case-insensitive way:
        * `True` can be set with `true`, `yes`, `on` and `y`.
        * `False` can be set with `false`, `off`, `n`, `no`, `non`, `none` and `""` (empty string).
    * `SequenceParameter` can specify their own delimiter (e.g. `,`), so the environment variable
      string is processed into a list.
    * `MapParameter` and `ObjectParameter` do not support being set with environment variables.
* `ArgParseRawParameter`: These are a bit different because there is no automated mechanism that
  ties a given command line flag to the context object. This means that if you add a new setting
  to the `Context` class and you want that available in the CLI as a command line flag, you have
  to add it yourself. If that's the case, refer to `conda.cli.conda_argparse` and make sure that
  the `dest` value of your `argparse.Argument` matches the attribute name in `Context`. This way,
  `Configuration.__init__` can take the `argparse.Namespace` object, turn it into a dictionary,
  and make it pass through the loading machinery.
