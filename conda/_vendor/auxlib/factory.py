"""A python implementation of the factory design pattern.  It's designed for use as a base class
for various types of data gateways.
"""
from __future__ import absolute_import, division, print_function

from .compat import with_metaclass
from .exceptions import InitializationError

__all__ = ['Factory']


class FactoryBase(object):

    @classmethod
    def initialize(cls, context, default_provider):
        cls.context = context
        cls._default_provider = (default_provider.__name__ if isinstance(default_provider, type)
                                 else str(default_provider))
        if not cls.is_registered_provider(cls._default_provider):
            raise RuntimeError("{0} is not a registered provider for "
                               "{1}".format(cls._default_provider, cls.__name__))

    @classmethod
    def get_instance(cls, provider=None):
        if not hasattr(cls, 'context'):
            raise InitializationError("RecordRepoFactory has not been initialized.")
        provider = provider.__name__ if isinstance(provider, type) else provider or cls._default_provider  # noqa
        return cls.providers[provider](cls.context)

    @classmethod
    def get_registered_provider_names(cls):
        return cls.providers.keys()

    @classmethod
    def get_registered_providers(cls):
        return cls.providers.values()

    @classmethod
    def is_registered_provider(cls, provider):
        if isinstance(provider, type):
            provider = provider.__name__
        return provider in cls.get_registered_provider_names()


class FactoryType(type):

    def __init__(cls, name, bases, attr):
        super(FactoryType, cls).__init__(name, bases, attr)
        if 'skip_registration' in cls.__dict__ and cls.skip_registration:
            pass  # we don't even care  # pragma: no cover
        elif cls.factory is None:
            # this must be the base implementation; add a factory object
            cls.factory = type(cls.__name__ + 'Factory', (FactoryBase, ),
                               {'providers': dict(), 'cache': dict()})
            if hasattr(cls, 'gateways'):
                cls.gateways.add(cls)
        else:
            # must be a derived object, register it as a provider in cls.factory
            cls.factory.providers[cls.__name__] = cls

    def __call__(cls, *args):
        if 'factory' in cls.__dict__:
            if args and args[0]:
                return cls.factory.get_instance(args[0])
            else:
                return cls.factory.get_instance()
        else:
            if not getattr(cls, 'do_cache', False):
                return super(FactoryType, cls).__call__(*args)
            cache_id = "{0}".format(cls.__name__)
            try:
                return cls.factory.cache[cache_id]
            except KeyError:
                instance = super(FactoryType, cls).__call__(*args)
                cls.factory.cache[cache_id] = instance
                return instance


@with_metaclass(FactoryType)
class Factory(object):
    skip_registration = True
    factory = None


# ## Document these ##
# __metaclass__
# factory
# skip_registration
# gateways
# do_cache

# TODO: add name parameter  --give example from transcomm client factory
