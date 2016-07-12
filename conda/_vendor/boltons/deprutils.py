# -*- coding: utf-8 -*-

"""
Note that DeprecationWarnings are ignored by default in Python
2.7/3.2+, so be sure to either un-ignore them in your code, or run
Python with the -Wd flag.
"""

import sys
from warnings import warn

ModuleType = type(sys)

# todo: only warn once


class DeprecatableModule(ModuleType):
    def __init__(self, module):
        name = module.__name__
        super(DeprecatableModule, self).__init__(name=name)
        self.__dict__.update(module.__dict__)

    def __getattribute__(self, name):
        get_attribute = super(DeprecatableModule, self).__getattribute__
        try:
            depros = get_attribute('_deprecated_members')
        except AttributeError:
            self._deprecated_members = depros = {}
        ret = get_attribute(name)
        message = depros.get(name)
        if message is not None:
            warn(message, DeprecationWarning, stacklevel=2)
        return ret


def deprecate_module_member(mod_name, name, message):
    module = sys.modules[mod_name]
    if not isinstance(module, DeprecatableModule):
        sys.modules[mod_name] = module = DeprecatableModule(module)
    module._deprecated_members[name] = message
    return
