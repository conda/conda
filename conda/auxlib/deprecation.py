# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from inspect import isbuiltin
from logging import getLogger
import sys
import warnings

log = getLogger(__name__)


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used."""
    if callable(func):
        def new_func(*args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning)  # turn off filter
            warnings.warn("Call to deprecated {0}.".format(func.__name__),
                          category=DeprecationWarning,
                          stacklevel=2)
            warnings.simplefilter('default', DeprecationWarning)  # reset filter
            return func(*args, **kwargs)
        new_func.__name__ = func.__name__
        new_func.__doc__ = func.__doc__
        new_func.__dict__.update(func.__dict__)
    else:
        raise NotImplementedError()
    return new_func


def deprecated_import(module_name):
    warnings.simplefilter('always', ImportWarning)  # turn off filter
    warnings.warn("Import of deprecated module {0}.".format(module_name),
                  category=ImportWarning)
    warnings.simplefilter('default', ImportWarning)  # reset filter


def import_and_wrap_deprecated(module_name, module_dict, warn_import=True):
    """
    Usage:
        import_and_wrap_deprecated('conda.common.connection', locals())
        # looks for conda.common.connection.__all__
    """
    if warn_import:
        deprecated_import(module_name)

    from importlib import import_module
    module = import_module(module_name)
    for attr in module.__all__:
        module_dict[attr] = deprecated(getattr(module, attr))


def deprecate_module_with_proxy(module_name, module_dict, deprecated_attributes=None):
    """
    Usage:
        deprecate_module_with_proxy(__name__, locals())  # at bottom of module
    """
    def _ModuleProxy(module, depr):
        """Return a wrapped object that warns about deprecated accesses"""
        # http://stackoverflow.com/a/922693/2127762
        class Wrapper(object):
            def __getattr__(self, attr):
                if depr is None or attr in depr:
                    warnings.warn("Property %s is deprecated" % attr)

                return getattr(module, attr)

            def __setattr__(self, attr, value):
                if depr is None or attr in depr:
                    warnings.warn("Property %s is deprecated" % attr)
                return setattr(module, attr, value)
        return Wrapper()

    deprecated_import(module_name)

    deprs = set()
    for key in deprecated_attributes or module_dict:
        if key.startswith('_'):
            continue
        if callable(module_dict[key]) and not isbuiltin(module_dict[key]):
            module_dict[key] = deprecated(module_dict[key])
        else:
            deprs.add(key)
    sys.modules[module_name] = _ModuleProxy(sys.modules[module_name], deprs or None)
