# -*- coding: utf-8 -*-
"""Python's built-in :mod:`functools` module builds several useful
utilities on top of Python's first-class function
support. ``funcutils`` generally stays in the same vein, adding to and
correcting Python's standard metaprogramming facilities.
"""
from __future__ import print_function

import sys
import re
import inspect
import functools
import itertools
from types import MethodType, FunctionType

try:
    xrange
    make_method = MethodType
except NameError:
    # Python 3
    make_method = lambda desc, obj, obj_type: MethodType(desc, obj)
    basestring = (str, bytes)  # Python 3 compat
    _IS_PY2 = False
else:
    _IS_PY2 = True


def get_module_callables(mod, ignore=None):
    """Returns two maps of (*types*, *funcs*) from *mod*, optionally
    ignoring based on the :class:`bool` return value of the *ignore*
    callable. *mod* can be a string name of a module in
    :data:`sys.modules` or the module instance itself.
    """
    if isinstance(mod, basestring):
        mod = sys.modules[mod]
    types, funcs = {}, {}
    for attr_name in dir(mod):
        if ignore and ignore(attr_name):
            continue
        try:
            attr = getattr(mod, attr_name)
        except Exception:
            continue
        try:
            attr_mod_name = attr.__module__
        except AttributeError:
            continue
        if attr_mod_name != mod.__name__:
            continue
        if isinstance(attr, type):
            types[attr_name] = attr
        elif callable(attr):
            funcs[attr_name] = attr
    return types, funcs


def mro_items(type_obj):
    """Takes a type and returns an iterator over all class variables
    throughout the type hierarchy (respecting the MRO).

    >>> sorted(set([k for k, v in mro_items(int) if not k.startswith('__') and not callable(v)]))
    ['denominator', 'imag', 'numerator', 'real']
    """
    # TODO: handle slots?
    return itertools.chain.from_iterable(ct.__dict__.items()
                                         for ct in type_obj.__mro__)


def dir_dict(obj, raise_exc=False):
    """Return a dictionary of attribute names to values for a given
    object. Unlike ``obj.__dict__``, this function returns all
    attributes on the object, including ones on parent classes.
    """
    # TODO: separate function for handling descriptors on types?
    ret = {}
    for k in dir(obj):
        try:
            ret[k] = getattr(obj, k)
        except Exception:
            if raise_exc:
                raise
    return ret


def copy_function(orig, copy_dict=True):
    """Returns a shallow copy of the function, including code object,
    globals, closure, etc.

    >>> func = lambda: func
    >>> func() is func
    True
    >>> func_copy = copy_function(func)
    >>> func_copy() is func
    True
    >>> func_copy is not func
    True

    Args:
        orig (function): The function to be copied. Must be a
            function, not just any method or callable.
        copy_dict (bool): Also copy any attributes set on the function
            instance. Defaults to ``True``.
    """
    ret = FunctionType(orig.__code__,
                       orig.__globals__,
                       name=orig.__name__,
                       argdefs=getattr(orig, "__defaults__", None),
                       closure=getattr(orig, "__closure__", None))
    if copy_dict:
        ret.__dict__.update(orig.__dict__)
    return ret


def partial_ordering(cls):
    """Class decorator, similar to :func:`functools.total_ordering`,
    except it is used to define `partial orderings`_ (i.e., it is
    possible that *x* is neither greater than, equal to, or less than
    *y*). It assumes the presence of the ``__le__()`` and ``__ge__()``
    method, but nothing else. It will not override any existing
    additional comparison methods.

    .. _partial orderings: https://en.wikipedia.org/wiki/Partially_ordered_set

    >>> @partial_ordering
    ... class MySet(set):
    ...     def __le__(self, other):
    ...         return self.issubset(other)
    ...     def __ge__(self, other):
    ...         return self.issuperset(other)
    ...
    >>> a = MySet([1,2,3])
    >>> b = MySet([1,2])
    >>> c = MySet([1,2,4])
    >>> b < a
    True
    >>> b > a
    False
    >>> b < c
    True
    >>> a < c
    False
    >>> c > a
    False
    """
    def __lt__(self, other): return self <= other and not self >= other
    def __gt__(self, other): return self >= other and not self <= other
    def __eq__(self, other): return self >= other and self <= other

    if not hasattr(cls, '__lt__'): cls.__lt__ = __lt__
    if not hasattr(cls, '__gt__'): cls.__gt__ = __gt__
    if not hasattr(cls, '__eq__'): cls.__eq__ = __eq__

    return cls


class InstancePartial(functools.partial):
    """:class:`functools.partial` is a huge convenience for anyone
    working with Python's great first-class functions. It allows
    developers to curry arguments and incrementally create simpler
    callables for a variety of use cases.

    Unfortunately there's one big gap in its usefulness:
    methods. Partials just don't get bound as methods and
    automatically handed a reference to ``self``. The
    ``InstancePartial`` type remedies this by inheriting from
    :class:`functools.partial` and implementing the necessary
    descriptor protocol. There are no other differences in
    implementation or usage. :class:`CachedInstancePartial`, below,
    has the same ability, but is slightly more efficient.

    """
    def __get__(self, obj, obj_type):
        return make_method(self, obj, obj_type)


class CachedInstancePartial(functools.partial):
    """The ``CachedInstancePartial`` is virtually the same as
    :class:`InstancePartial`, adding support for method-usage to
    :class:`functools.partial`, except that upon first access, it
    caches the bound method on the associated object, speeding it up
    for future accesses, and bringing the method call overhead to
    about the same as non-``partial`` methods.

    See the :class:`InstancePartial` docstring for more details.
    """
    def __get__(self, obj, obj_type):
        # These assignments could've been in __init__, but there was
        # no simple way to do it without breaking one of PyPy or Py3.
        self.__name__ = None
        self.__doc__ = self.func.__doc__
        self.__module__ = self.func.__module__

        name = self.__name__
        if name is None:
            for k, v in mro_items(obj_type):
                if v is self:
                    self.__name__ = name = k
        if obj is None:
            return make_method(self, obj, obj_type)
        try:
            # since this is a data descriptor, this block
            # is probably only hit once (per object)
            return obj.__dict__[name]
        except KeyError:
            obj.__dict__[name] = ret = make_method(self, obj, obj_type)
            return ret

partial = CachedInstancePartial


# # #
# # # Function builder
# # #


def wraps(func, injected=None, **kw):
    """Modeled after the built-in :func:`functools.wraps`, this function is
    used to make your decorator's wrapper functions reflect the
    wrapped function's:

      * Name
      * Documentation
      * Module
      * Signature

    The built-in :func:`functools.wraps` copies the first three, but
    does not copy the signature. This version of ``wraps`` can copy
    the inner function's signature exactly, allowing seamless usage
    and :mod:`introspection <inspect>`. Usage is identical to the
    built-in version::

        >>> from boltons.funcutils import wraps
        >>>
        >>> def print_return(func):
        ...     @wraps(func)
        ...     def wrapper(*args, **kwargs):
        ...         ret = func(*args, **kwargs)
        ...         print(ret)
        ...         return ret
        ...     return wrapper
        ...
        >>> @print_return
        ... def example():
        ...     '''docstring'''
        ...     return 'example return value'
        >>>
        >>> val = example()
        example return value
        >>> example.__name__
        'example'
        >>> example.__doc__
        'docstring'

    In addition, the boltons version of wraps supports modifying the
    outer signature based on the inner signature. By passing a list of
    *injected* argument names, those arguments will be removed from
    the outer wrapper's signature, allowing your decorator to provide
    arguments that aren't passed in.

    Args:

        func (function): The callable whose attributes are to be copied.
        injected (list): An optional list of argument names which
            should not appear in the new wrapper's signature.
        update_dict(bool): Whether to copy other, non-standard
            attributes of *func* over to the wrapper. Defaults to True.

    For more in-depth wrapping of functions, see the
    :class:`FunctionBuilder` type, on which wraps was built.
    """
    if injected is None:
        injected = []
    elif isinstance(injected, basestring):
        injected = [injected]

    update_dict = kw.pop('update_dict', True)
    if kw:
        raise TypeError('unexpected kwargs: %r' % kw.keys())

    fb = FunctionBuilder.from_func(func)
    for arg in injected:
        fb.remove_arg(arg)

    fb.body = 'return _call(%s)' % fb.get_invocation_str()

    def wrapper_wrapper(wrapper_func):
        execdict = dict(_call=wrapper_func, _func=func)
        fully_wrapped = fb.get_func(execdict, with_dict=update_dict)

        return fully_wrapped

    return wrapper_wrapper


class FunctionBuilder(object):
    """The FunctionBuilder type provides an interface for programmatically
    creating new functions, either based on existing functions or from
    scratch.

    Values are passed in at construction or set as attributes on the
    instance. For creating a new function based of an existing one,
    see the :meth:`~FunctionBuilder.from_func` classmethod. At any
    point, :meth:`~FunctionBuilder.get_func` can be called to get a
    newly compiled function, based on the values configured.

    >>> fb = FunctionBuilder('return_five', doc='returns the integer 5',
    ...                      body='return 5')
    >>> f = fb.get_func()
    >>> f()
    5
    >>> fb.varkw = 'kw'
    >>> f_kw = fb.get_func()
    >>> f_kw(ignored_arg='ignored_val')
    5

    Note that function signatures themselves changed quite a bit in
    Python 3, so several arguments are only applicable to
    FunctionBuilder in Python 3. Except for *name*, all arguments to
    the constructor are keyword arguments.

    Args:
        name (str): Name of the function.
        doc (str): `Docstring`_ for the function, defaults to empty.
        module (str): Name of the module from which this function was
            imported. Defaults to None.
        body (str): String version of the code representing the body
            of the function. Defaults to ``'pass'``, which will result
            in a function which does nothing and returns ``None``.
        args (list): List of argument names, defaults to empty list,
            denoting no arguments.
        varargs (str): Name of the catch-all variable for positional
            arguments. E.g., "args" if the resultant function is to have
            ``*args`` in the signature. Defaults to None.
        varkw (str): Name of the catch-all variable for keyword
            arguments. E.g., "kwargs" if the resultant function is to have
            ``**kwargs`` in the signature. Defaults to None.
        defaults (dict): A mapping of argument names to default values.
        kwonlyargs (list): Argument names which are only valid as
            keyword arguments. **Python 3 only.**
        kwonlydefaults (dict): A mapping, same as normal *defaults*,
            but only for the *kwonlyargs*. **Python 3 only.**
        annotations (dict): Mapping of type hints and so
            forth. **Python 3 only.**
        indent (int): Number of spaces with which to indent the
            function *body*. Values less than 1 will result in an error.
        dict (dict): Any other attributes which should be added to the
            functions compiled with this FunctionBuilder.

    All of these arguments are also made available as attributes which
    can be mutated as necessary.

    .. _Docstring: https://en.wikipedia.org/wiki/Docstring#Python

    """

    if _IS_PY2:
        _argspec_defaults = {'args': list,
                             'varargs': lambda: None,
                             'varkw': lambda: None,
                             'defaults': lambda: None}

        @classmethod
        def _argspec_to_dict(cls, f):
            args, varargs, varkw, defaults = inspect.getargspec(f)
            return {'args': args,
                    'varargs': varargs,
                    'varkw': varkw,
                    'defaults': defaults}

    else:
        _argspec_defaults = {'args': list,
                             'varargs': lambda: None,
                             'varkw': lambda: None,
                             'defaults': lambda: None,
                             'kwonlyargs': list,
                             'kwonlydefaults': dict,
                             'annotations': dict}

        @classmethod
        def _argspec_to_dict(cls, f):
            argspec = inspect.getfullargspec(f)
            return dict((attr, getattr(argspec, attr))
                        for attr in cls._argspec_defaults)

    _defaults = {'doc': str,
                 'dict': dict,
                 'module': lambda: None,
                 'body': lambda: 'pass',
                 'indent': lambda: 4}

    _defaults.update(_argspec_defaults)

    _compile_count = itertools.count()

    def __init__(self, name, **kw):
        self.name = name
        for a, default_factory in self._defaults.items():
            val = kw.pop(a, None)
            if val is None:
                val = default_factory()
            setattr(self, a, val)

        if kw:
            raise TypeError('unexpected kwargs: %r' % kw.keys())
        return

    # def get_argspec(self):  # TODO

    if _IS_PY2:
        def get_sig_str(self):
            return inspect.formatargspec(self.args, self.varargs,
                                         self.varkw, [])

        def get_invocation_str(self):
            return inspect.formatargspec(self.args, self.varargs,
                                         self.varkw, [])[1:-1]
    else:
        def get_sig_str(self):
            return inspect.formatargspec(self.args,
                                         self.varargs,
                                         self.varkw,
                                         [],
                                         self.kwonlyargs,
                                         {},
                                         self.annotations)

        _KWONLY_MARKER = re.compile(r"""
        \*     # a star
        \s*    # followed by any amount of whitespace
        ,      # followed by a comma
        \s*    # followed by any amount of whitespace
        """, re.VERBOSE)

        def get_invocation_str(self):
            kwonly_pairs = None
            formatters = {}
            if self.kwonlyargs:
                kwonly_pairs = dict((arg, arg)
                                    for arg in self.kwonlyargs)
                formatters['formatvalue'] = lambda value: '=' + value

            sig = inspect.formatargspec(self.args,
                                        self.varargs,
                                        self.varkw,
                                        [],
                                        kwonly_pairs,
                                        kwonly_pairs,
                                        {},
                                        **formatters)
            sig = self._KWONLY_MARKER.sub('', sig)
            return sig[1:-1]

    @classmethod
    def from_func(cls, func):
        """Create a new FunctionBuilder instance based on an existing
        function. The original function will not be stored or
        modified.
        """
        # TODO: copy_body? gonna need a good signature regex.
        # TODO: might worry about __closure__?
        kwargs = {'name': func.__name__,
                  'doc': func.__doc__,
                  'module': func.__module__,
                  'dict': getattr(func, '__dict__', {})}

        kwargs.update(cls._argspec_to_dict(func))

        return cls(**kwargs)

    def get_func(self, execdict=None, add_source=True, with_dict=True):
        """Compile and return a new function based on the current values of
        the FunctionBuilder.

        Args:
            execdict (dict): The dictionary representing the scope in
                which the compilation should take place. Defaults to an empty
                dict.
            add_source (bool): Whether to add the source used to a
                special ``__source__`` attribute on the resulting
                function. Defaults to True.
            with_dict (bool): Add any custom attributes, if
                applicable. Defaults to True.

        To see an example of usage, see the implementation of
        :func:`~boltons.funcutils.wraps`.
        """
        execdict = execdict or {}
        body = self.body or self._default_body

        tmpl = 'def {name}{sig_str}:'
        if self.doc:
            tmpl += '\n    """{doc}"""'
        tmpl += '\n{body}'

        body = _indent(self.body, ' ' * self.indent)

        name = self.name.replace('<', '_').replace('>', '_')  # lambdas
        src = tmpl.format(name=name, sig_str=self.get_sig_str(),
                          doc=self.doc, body=body)
        self._compile(src, execdict)
        func = execdict[name]

        func.__name__ = self.name
        func.__doc__ = self.doc
        func.__defaults__ = self.defaults
        if not _IS_PY2:
            func.__kwdefaults__ = self.kwonlydefaults

        if with_dict:
            func.__dict__.update(self.dict)
        func.__module__ = self.module
        # TODO: caller module fallback?

        if add_source:
            func.__source__ = src

        return func

    def get_defaults_dict(self):
        """Get a dictionary of function arguments with defaults and the
        respective values.
        """
        ret = dict(reversed(list(zip(reversed(self.args),
                                     reversed(self.defaults or [])))))
        return ret

    def remove_arg(self, arg_name):
        """Remove an argument from this FunctionBuilder's argument list. The
        resulting function will have one less argument per call to
        this function.

        Args:
            arg_name (str): The name of the argument to remove.

        Raises a :exc:`ValueError` if the argument is not present.

        """
        d_dict = self.get_defaults_dict()
        try:
            self.args.remove(arg_name)
        except ValueError:
            raise ValueError('arg %r not found in %s argument list: %r'
                             % (arg_name, self.name, self.args))
        d_dict.pop(arg_name, None)
        self.defaults = tuple([d_dict[a] for a in self.args if a in d_dict])
        return

    def _compile(self, src, execdict):
        filename = ('<boltons.funcutils.FunctionBuilder-%d>'
                    % (next(self._compile_count),))
        try:
            code = compile(src, filename, 'single')
            exec(code, execdict)
        except Exception:
            raise
        return execdict


def _indent(text, margin, newline='\n', key=bool):
    "based on boltons.strutils.indent"
    indented_lines = [(margin + line if key(line) else line)
                      for line in text.splitlines()]
    return newline.join(indented_lines)


# end funcutils.py
