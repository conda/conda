# -*- coding: utf-8 -*-
"""
This module provides serializable, validatable, type-enforcing domain objects and data
transfer objects. It has many of the same motivations as the python
`Marshmallow <http://marshmallow.readthedocs.org/en/latest/why.html>`_ package. It is most
similar to `Schematics <http://schematics.readthedocs.io/>`_.

========
Tutorial
========

Chapter 1: Entity and Field Basics
----------------------------------

    >>> class Color(Enum):
    ...     blue = 0
    ...     black = 1
    ...     red = 2
    >>> class Car(Entity):
    ...     weight = NumberField(required=False)
    ...     wheels = IntField(default=4, validation=lambda x: 3 <= x <= 4)
    ...     color = EnumField(Color)

    >>> # create a new car object
    >>> car = Car(color=Color.blue, weight=4242.46)
    >>> car
    Car(weight=4242.46, color=0)

    >>> # it has 4 wheels, all by default
    >>> car.wheels
    4

    >>> # but a car can't have 5 wheels!
    >>> #  the `validation=` field is a simple callable that returns a
    >>> #  boolean based on validity
    >>> car.wheels = 5
    Traceback (most recent call last):
    ValidationError: Invalid value 5 for wheels

    >>> # we can call .dump() on car, and just get back a standard
    >>> #  python dict actually, it's an ordereddict to match attribute
    >>> #  declaration order
    >>> type(car.dump())
    <class '...OrderedDict'>
    >>> car.dump()
    OrderedDict([('weight', 4242.46), ('wheels', 4), ('color', 0)])

    >>> # and json too (note the order!)
    >>> car.json()
    '{"weight": 4242.46, "wheels": 4, "color": 0}'

    >>> # green cars aren't allowed
    >>> car.color = "green"
    Traceback (most recent call last):
    ValidationError: 'green' is not a valid Color

    >>> # but black cars are!
    >>> car.color = "black"
    >>> car.color
    <Color.black: 1>

    >>> # car.color really is an enum, promise
    >>> type(car.color)
    <enum 'Color'>

    >>> # enum assignment can be with any of (and preferentially)
    >>> #   (1) an enum literal,
    >>> #   (2) a valid enum value, or
    >>> #   (3) a valid enum name
    >>> car.color = Color.blue; car.color.value
    0
    >>> car.color = 1; car.color.name
    'black'

    >>> # let's do a round-trip marshalling of this thing
    >>> same_car = Car.from_json(car.json())  # or equally Car.from_json(json.dumps(car.dump()))
    >>> same_car == car
    True

    >>> # actually, they're two different instances
    >>> same_car is not car
    True

    >>> # this works too
    >>> cloned_car = Car(**car.dump())
    >>> cloned_car == car
    True

    >>> # while we're at it, these are all equivalent too
    >>> car == Car.from_objects(car)
    True
    >>> car == Car.from_objects({"weight": 4242.46, "wheels": 4, "color": 1})
    True
    >>> car == Car.from_json('{"weight": 4242.46, "color": 1}')
    True

    >>> # .from_objects() even lets you stack and combine objects
    >>> class DumbClass:
    ...     color = 0
    ...     wheels = 3
    >>> Car.from_objects(DumbClass(), dict(weight=2222, color=1))
    Car(weight=2222, wheels=3, color=0)
    >>> # and also pass kwargs that override properties pulled
    >>> #  off any objects
    >>> Car.from_objects(DumbClass(), {'weight': 2222, 'color': 1}, color=2, weight=33)
    Car(weight=33, wheels=3, color=2)


Chapter 2: Entity and Field Composition
---------------------------------------

    >>> # now let's get fancy
    >>> # a ComposableField "nests" another valid Entity
    >>> # a ListField's first argument is a "generic" type,
    >>> #   which can be a valid Entity, any python primitive
    >>> #   type, or a list of Entities/types
    >>> class Fleet(Entity):
    ...     boss_car = ComposableField(Car)
    ...     cars = ListField(Car)

    >>> # here's our fleet of company cars
    >>> company_fleet = Fleet(boss_car=Car(color='red'), cars=[car, same_car, cloned_car])
    >>> company_fleet.pretty_json()  #doctest: +SKIP
    {
      "boss_car": {
        "wheels": 4
        "color": 2,
      },
      "cars": [
        {
          "weight": 4242.46,
          "wheels": 4
          "color": 1,
        },
        {
          "weight": 4242.46,
          "wheels": 4
          "color": 1,
        },
        {
          "weight": 4242.46,
          "wheels": 4
          "color": 1,
        }
      ]
    }

    >>> # the boss' car is red of course (and it's still an Enum)
    >>> company_fleet.boss_car.color.name
    'red'

    >>> # and there are three cars left for the employees
    >>> len(company_fleet.cars)
    3


Chapter 3: Immutability
-----------------------

    >>> class ImmutableCar(ImmutableEntity):
    ...     wheels = IntField(default=4, validation=lambda x: 3 <= x <= 4)
    ...     color = EnumField(Color)
    >>> icar = ImmutableCar.from_objects({'wheels': 3, 'color': 'blue'})
    >>> icar
    ImmutableCar(wheels=3, color=0)

    >>> icar.wheels = 4
    Traceback (most recent call last):
    AttributeError: Assignment not allowed. ImmutableCar is immutable.

    >>> class FixedWheelCar(Entity):
    ...     wheels = IntField(default=4, immutable=True)
    ...     color = EnumField(Color)
    >>> fwcar = FixedWheelCar.from_objects(icar)
    >>> fwcar.json()
    '{"wheels": 3, "color": 0}'

    >>> # repainting the car is easy
    >>> fwcar.color = Color.red
    >>> fwcar.color.name
    'red'

    >>> # can't really change the number of wheels though
    >>> fwcar.wheels = 18
    Traceback (most recent call last):
    AttributeError: The wheels field is immutable.


Chapter X: The del and null Weeds
---------------------------------

    >>> old_date = lambda: isoparse('1982-02-17')
    >>> class CarBattery(Entity):
    ...     # NOTE: default value can be a callable!
    ...     first_charge = DateField(required=False)  # default=None, nullable=False
    ...     latest_charge = DateField(default=old_date, nullable=True)  # required=True
    ...     expiration = DateField(default=old_date, required=False, nullable=False)

    >>> # starting point
    >>> battery = CarBattery()
    >>> battery
    CarBattery()
    >>> battery.json()
    '{"latest_charge": "1982-02-17T00:00:00", "expiration": "1982-02-17T00:00:00"}'

    >>> # first_charge is not assigned a default value. Once one is assigned, it can be deleted,
    >>> #   but it can't be made null.
    >>> battery.first_charge = isoparse('2016-03-23')
    >>> battery
    CarBattery(first_charge=datetime.datetime(2016, 3, 23, 0, 0))
    >>> battery.first_charge = None
    Traceback (most recent call last):
    ValidationError: Value for first_charge not given or invalid.
    >>> del battery.first_charge
    >>> battery
    CarBattery()

    >>> # latest_charge can be null, but it can't be deleted. The default value is a callable.
    >>> del battery.latest_charge
    Traceback (most recent call last):
    AttributeError: The latest_charge field is required and cannot be deleted.
    >>> battery.latest_charge = None
    >>> battery.json()
    '{"latest_charge": null, "expiration": "1982-02-17T00:00:00"}'

    >>> # expiration is assigned by default, can't be made null, but can be deleted.
    >>> battery.expiration
    datetime.datetime(1982, 2, 17, 0, 0)
    >>> battery.expiration = None
    Traceback (most recent call last):
    ValidationError: Value for expiration not given or invalid.
    >>> del battery.expiration
    >>> battery.json()
    '{"latest_charge": null}'


"""
from __future__ import absolute_import, division, print_function

from collections import Iterable, Sequence, Mapping
from copy import deepcopy
from datetime import datetime
from enum import Enum
from functools import reduce
from json import JSONEncoder, dumps as json_dumps, loads as json_loads
from logging import getLogger

from ._vendor.boltons.timeutils import isoparse
from .collection import AttrDict, frozendict, make_immutable
from .compat import (integer_types, iteritems, itervalues, odict, string_types, text_type,
                     with_metaclass, isiterable)
from .exceptions import Raise, ValidationError
from .ish import find_or_none
from .logz import DumpEncoder
from .type_coercion import maybecall

log = getLogger(__name__)

__all__ = [
    "Entity", "ImmutableEntity", "Field",
    "BooleanField", "BoolField", "IntegerField", "IntField",
    "NumberField", "StringField", "DateField",
    "EnumField", "ListField", "MapField", "ComposableField",
]

KEY_OVERRIDES_MAP = "__key_overrides__"


NOTES = """

Current deficiencies to schematics:
  - no get_mock_object method
  - no context-dependent serialization or MultilingualStringType
  - name = StringType(serialized_name='person_name', alternate_names=['human_name'])
  - name = StringType(serialize_when_none=False)
  - more flexible validation error messages
  - field validation can depend on other fields
  - 'roles' containing blacklists for .dump() and .json()
    __roles__ = {
        EntityRole.registered_name: Blacklist('field1', 'field2'),
        EntityRole.another_registered_name: Whitelist('field3', 'field4'),
    }


TODO:
  - alternate field names
  - add dump_if_null field option
  - add help/description parameter to Field
  - consider leveraging slots
  - collect all validation errors before raising
  - Allow returning string error message for validation instead of False
  - profile and optimize
  - use boltons instead of dateutil
  - correctly implement copy and deepcopy on fields and Entity, DictSafeMixin
    http://stackoverflow.com/questions/1500718/what-is-the-right-way-to-override-the-copy-deepcopy-operations-on-an-object-in-p


Optional Field Properties:
  - validation = None
  - default = None
  - required = True
  - in_dump = True
  - nullable = False

Behaviors:
  - Nullable is a "hard" setting, in that the value is either always or never allowed to be None.
  - What happens then if required=False and nullable=False?
      - The object can be init'd without a value (though not with a None value).
        getattr throws AttributeError
      - Any assignment must be not None.


  - Setting a value to None doesn't "unset" a value.  (That's what del is for.)  And you can't
    del a value if required=True, nullable=False, default=None.

  - If a field is not required, del does *not* "unmask" the default value.  Instead, del
    removes the value from the object entirely.  To get back the default value, need to recreate
    the object.  Entity.from_objects(old_object)


  - Disabling in_dump is a "hard" setting, in that with it disabled the field will never get
    dumped.  With it enabled, the field may or may not be dumped depending on its value and other
    settings.

  - Required is a "hard" setting, in that if True, a valid value or default must be provided. None
    is only a valid value or default if nullable is True.

  - In general, nullable means that None is a valid value.
    - getattr returns None instead of raising Attribute error
    - If in_dump, field is given with null value.
    - If default is not None, assigning None clears a previous assignment. Future getattrs return
      the default value.
    - What does nullable mean with default=None and required=True? Does instantiation raise
      an error if assignment not made on init? Can IntField(nullable=True) be init'd?

  - If required=False and nullable=False, field will only be in dump if field!=None.
    Also, getattr raises AttributeError.
  - If required=False and nullable=True, field will be in dump if field==None.

  - If in_dump is True, does default value get dumped:
    - if no assignment, default exists
    - if nullable, and assigned None
  - How does optional validation work with nullable and assigning None?
  - When does gettattr throw AttributeError, and when does it return None?



"""


class Field(object):
    """
    Fields are doing something very similar to boxing and unboxing
    of c#/java primitives.  __set__ should take a "primitive" or "raw" value and create a "boxed"
    or "programatically useable" value of it.  While __get__ should return the boxed value,
    dump in turn should unbox the value into a primitive or raw value.

    Arguments:
        types_ (primitive literal or type or sequence of types):
        default (any, callable, optional):  If default is callable, it's guaranteed to return a
            valid value at the time of Entity creation.
        required (boolean, optional):
        validation (callable, optional):
        dump (boolean, optional):
    """

    # Used to track order of field declarations. Supporting python 2.7, so can't rely
    #   on __prepare__.  Strategy lifted from http://stackoverflow.com/a/4460034/2127762
    _order_helper = 0

    def __init__(self, default=None, required=True, validation=None,
                 in_dump=True, nullable=False, immutable=False):
        self._required = required
        self._validation = validation
        self._in_dump = in_dump
        self._nullable = nullable
        self._immutable = immutable
        self._default = default if callable(default) else self.box(None, default)
        if default is not None:
            self.validate(None, self.box(None, maybecall(default)))

        self._order_helper = Field._order_helper
        Field._order_helper += 1

    @property
    def name(self):
        try:
            return self._name
        except AttributeError:
            log.error("The name attribute has not been set for this field. "
                      "Call set_name at class creation time.")
            raise

    def set_name(self, name):
        self._name = name
        return self

    def __get__(self, instance, instance_type):
        try:
            if instance is None:  # if calling from the class object
                val = getattr(instance_type, KEY_OVERRIDES_MAP)[self.name]
            else:
                val = instance.__dict__[self.name]
        except AttributeError:
            log.error("The name attribute has not been set for this field.")
            raise AttributeError("The name attribute has not been set for this field.")
        except KeyError:
            if self.default is not None:
                val = maybecall(self.default)  # default *can* be a callable
            elif self._nullable:
                return None
            else:
                raise AttributeError("A value for {0} has not been set".format(self.name))
        if val is None and not self.nullable:
            # means the "tricky edge case" was activated in __delete__
            raise AttributeError("The {0} field has been deleted.".format(self.name))
        return self.unbox(instance, instance_type, val)

    def __set__(self, instance, val):
        if self.immutable and instance._initd:
            raise AttributeError("The {0} field is immutable.".format(self.name))
        # validate will raise an exception if invalid
        # validate will return False if the value should be removed
        instance.__dict__[self.name] = self.validate(instance, self.box(instance, val))

    def __delete__(self, instance):
        if self.immutable and instance._initd:
            raise AttributeError("The {0} field is immutable.".format(self.name))
        elif self.required:
            raise AttributeError("The {0} field is required and cannot be deleted."
                                 .format(self.name))
        elif not self.nullable:
            # tricky edge case
            # given a field Field(default='some value', required=False, nullable=False)
            # works together with Entity.dump() logic for selecting fields to include in dump
            # `if value is not None or field.nullable`
            instance.__dict__[self.name] = None
        else:
            instance.__dict__.pop(self.name, None)

    def box(self, instance, val):
        return val

    def unbox(self, instance, instance_type, val):
        return val

    def dump(self, val):
        return val

    def validate(self, instance, val):
        """

        Returns:
            True: if val is valid

        Raises:
            ValidationError
        """
        # note here calling, but not assigning; could lead to unexpected behavior
        if isinstance(val, self._type) and (self._validation is None or self._validation(val)):
            return val
        elif val is None and self.nullable:
            return val
        else:
            raise ValidationError(getattr(self, 'name', 'undefined name'), val)

    @property
    def required(self):
        return self._required

    @property
    def type(self):
        return self._type

    @property
    def default(self):
        return self._default

    @property
    def in_dump(self):
        return self._in_dump

    @property
    def nullable(self):
        return self.is_nullable

    @property
    def is_nullable(self):
        return self._nullable

    @property
    def immutable(self):
        return self._immutable


class BooleanField(Field):
    _type = bool

    def box(self, instance, val):
        return None if val is None else bool(val)

BoolField = BooleanField


class IntegerField(Field):
    _type = integer_types

IntField = IntegerField


class NumberField(Field):
    _type = integer_types + (float, complex)


class StringField(Field):
    _type = string_types

    def box(self, instance, val):
        return text_type(val) if isinstance(val, NumberField._type) else val


class DateField(Field):
    _type = datetime

    def box(self, instance, val):
        try:
            return isoparse(val) if isinstance(val, string_types) else val
        except ValueError as e:
            raise ValidationError(val, msg=e)

    def dump(self, val):
        return None if val is None else val.isoformat()


class EnumField(Field):

    def __init__(self, enum_class, default=None, required=True, validation=None,
                 in_dump=True, nullable=False, immutable=False):
        if not issubclass(enum_class, Enum):
            raise ValidationError(None, msg="enum_class must be an instance of Enum")
        self._type = enum_class
        super(EnumField, self).__init__(default, required, validation,
                                        in_dump, nullable, immutable)

    def box(self, instance, val):
        if val is None:
            # let the required/nullable logic handle validation for this case
            return None
        try:
            # try to box using val as an Enum name
            return val if isinstance(val, self._type) else self._type(val)
        except ValueError as e1:
            try:
                # try to box using val as an Enum value
                return self._type[val]
            except KeyError:
                raise ValidationError(val, msg=e1)

    def dump(self, val):
        return None if val is None else val.value


class ListField(Field):
    _type = tuple

    def __init__(self, element_type, default=None, required=True, validation=None,
                 in_dump=True, nullable=False, immutable=False):
        self._element_type = element_type
        super(ListField, self).__init__(default, required, validation,
                                        in_dump, nullable, immutable)

    def box(self, instance, val):
        if val is None:
            return None
        elif isinstance(val, string_types):
            raise ValidationError("Attempted to assign a string to ListField {0}"
                                  "".format(self.name))
        elif isiterable(val):
            et = self._element_type
            if isinstance(et, type) and issubclass(et, Entity):
                return self._type(v if isinstance(v, et) else et(**v) for v in val)
            else:
                return make_immutable(val) if self.immutable else self._type(val)
        else:
            raise ValidationError(val, msg="Cannot assign a non-iterable value to "
                                           "{0}".format(self.name))

    def unbox(self, instance, instance_type, val):
        return self._type() if val is None and not self.nullable else val

    def dump(self, val):
        if isinstance(self._element_type, type) and issubclass(self._element_type, Entity):
            return self._type(v.dump() for v in val)
        else:
            return val

    def validate(self, instance, val):
        if val is None:
            if not self.nullable:
                raise ValidationError(self.name, val)
            return None
        else:
            val = super(ListField, self).validate(instance, val)
            et = self._element_type
            self._type(Raise(ValidationError(self.name, el, et)) for el in val
                       if not isinstance(el, et))
            return val


class MutableListField(ListField):
    _type = list


class MapField(Field):
    _type = frozendict

    def __init__(self, default=None, required=True, validation=None,
                 in_dump=True, nullable=False):
        super(MapField, self).__init__(default, required, validation, in_dump, nullable, True)

    def box(self, instance, val):
        # TODO: really need to make this recursive to make any lists or maps immutable
        if val is None:
            return self._type()
        elif isiterable(val):
            val = make_immutable(val)
            if not isinstance(val, Mapping):
                raise ValidationError(val, msg="Cannot assign a non-iterable value to "
                                               "{0}".format(self.name))
            return val
        else:
            raise ValidationError(val, msg="Cannot assign a non-iterable value to "
                                           "{0}".format(self.name))



class ComposableField(Field):

    def __init__(self, field_class, default=None, required=True, validation=None,
                 in_dump=True, nullable=False, immutable=False):
        self._type = field_class
        super(ComposableField, self).__init__(default, required, validation,
                                              in_dump, nullable, immutable)

    def box(self, instance, val):
        if val is None:
            return None
        if isinstance(val, self._type):
            return val
        else:
            # assuming val is a dict now
            try:
                # if there is a key named 'self', have to rename it
                if hasattr(val, 'pop'):
                    val['slf'] = val.pop('self')
            except KeyError:
                pass  # no key of 'self', so no worries
            return val if isinstance(val, self._type) else self._type(**val)

    def dump(self, val):
        return None if val is None else val.dump()


class EntityType(type):

    @staticmethod
    def __get_entity_subclasses(bases):
        try:
            return [base for base in bases if issubclass(base, Entity) and base is not Entity]
        except NameError:
            # NameError: global name 'Entity' is not defined
            return ()

    def __new__(mcs, name, bases, dct):
        # if we're about to mask a field that's already been created with something that's
        #  not a field, then assign it to an alternate variable name
        non_field_keys = (key for key, value in iteritems(dct)
                          if not isinstance(value, Field) and not key.startswith('__'))
        entity_subclasses = EntityType.__get_entity_subclasses(bases)
        if entity_subclasses:
            keys_to_override = [key for key in non_field_keys
                                if any(isinstance(base.__dict__.get(key), Field)
                                       for base in entity_subclasses)]
            dct[KEY_OVERRIDES_MAP] = dict((key, dct.pop(key)) for key in keys_to_override)
        else:
            dct[KEY_OVERRIDES_MAP] = dict()

        return super(EntityType, mcs).__new__(mcs, name, bases, dct)

    def __init__(cls, name, bases, attr):
        super(EntityType, cls).__init__(name, bases, attr)
        fields = odict(cls.__fields__) if hasattr(cls, '__fields__') else odict()
        fields.update(sorted(((name, field.set_name(name))
                                      for name, field in iteritems(cls.__dict__)
                                      if isinstance(field, Field)),
                                     key=lambda item: item[1]._order_helper))
        cls.__fields__ = frozendict(fields)
        if hasattr(cls, '__register__'):
            cls.__register__()

    def __call__(cls, *args, **kwargs):
        instance = super(EntityType, cls).__call__(*args, **kwargs)
        setattr(instance, '_{0}__initd'.format(cls.__name__), True)
        return instance

    @property
    def fields(cls):
        return cls.__fields__.keys()


@with_metaclass(EntityType)
class Entity(object):
    __fields__ = odict()
    _lazy_validate = False

    def __init__(self, **kwargs):
        for key, field in iteritems(self.__fields__):
            try:
                setattr(self, key, kwargs[key])
            except KeyError:
                # handle the case of fields inherited from subclass but overrode on class object
                if key in getattr(self, KEY_OVERRIDES_MAP):
                    setattr(self, key, getattr(self, KEY_OVERRIDES_MAP)[key])
                elif field.required and field.default is None:
                    raise ValidationError(key, msg="{0} requires a {1} field. Instantiated with "
                                                   "{2}".format(self.__class__.__name__,
                                                                key, kwargs))
            except ValidationError:
                if kwargs[key] is not None or field.required:
                    raise
        if not self._lazy_validate:
            self.validate()

    @classmethod
    def from_objects(cls, *objects, **override_fields):
        init_vars = dict()
        search_maps = tuple(AttrDict(o) if isinstance(o, dict) else o
                            for o in ((override_fields,) + objects))
        for key in cls.__fields__:
            init_vars[key] = find_or_none(key, search_maps)
        return cls(**init_vars)

    @classmethod
    def from_json(cls, json_str):
        return cls(**json_loads(json_str))

    @classmethod
    def load(cls, data_dict):
        return cls(**data_dict)

    def validate(self):
        # TODO: here, validate should only have to determine if the required keys are set
        try:
            reduce(lambda _, name: getattr(self, name),
                   (name for name, field in iteritems(self.__fields__) if field.required)
                   )
        except TypeError as e:
            if str(e) == "reduce() of empty sequence with no initial value":
                pass
        except AttributeError as e:
            raise ValidationError(None, msg=e)

    def __repr__(self):
        def _valid(key):
            # TODO: re-enable once aliases are implemented
            # if key.startswith('_'):
            #     return False
            try:
                getattr(self, key)
                return True
            except AttributeError:
                return False

        def _val(key):
            val = getattr(self, key)
            return repr(val.value) if isinstance(val, Enum) else repr(val)

        def _sort_helper(key):
            field = self.__fields__.get(key)
            return field._order_helper if field is not None else -1

        kwarg_str = ", ".join("{0}={1}".format(key, _val(key))
                              for key in sorted(self.__dict__, key=_sort_helper)
                              if _valid(key))
        return "{0}({1})".format(self.__class__.__name__, kwarg_str)

    @classmethod
    def __register__(cls):
        pass

    def json(self, indent=None, separators=None, **kwargs):
        return json_dumps(self, indent=indent, separators=separators, cls=DumpEncoder, **kwargs)

    def pretty_json(self, indent=2, separators=(',', ': '), **kwargs):
        return self.json(indent=indent, separators=separators, **kwargs)

    def dump(self):
        return odict((field.name, field.dump(value))
                     for field, value in ((field, getattr(self, field.name, None))
                                          for field in self.__dump_fields())
                     if value is not None or field.nullable)

    @classmethod
    def __dump_fields(cls):
        if '__dump_fields_cache' not in cls.__dict__:
            cls.__dump_fields_cache = tuple(field for field in itervalues(cls.__fields__)
                                            if field.in_dump)
        return cls.__dump_fields_cache

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        rando_default = 19274656290  # need an arbitrary but definite value if field does not exist
        return all(getattr(self, field, rando_default) == getattr(other, field, rando_default)
                   for field in self.__fields__)

    def __hash__(self):
        return sum(hash(getattr(self, field, None)) for field in self.__fields__)

    @property
    def _initd(self):
        return getattr(self, '_{0}__initd'.format(self.__class__.__name__), None)


class ImmutableEntity(Entity):

    def __setattr__(self, attribute, value):
        if self._initd:
            raise AttributeError("Assignment not allowed. {0} is immutable."
                                 .format(self.__class__.__name__))
        super(ImmutableEntity, self).__setattr__(attribute, value)

    def __delattr__(self, item):
        if self._initd:
            raise AttributeError("Deletion not allowed. {0} is immutable."
                                 .format(self.__class__.__name__))
        super(ImmutableEntity, self).__delattr__(item)


class DictSafeMixin(object):

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, key):
        delattr(self, key)

    def get(self, item, default=None):
        return getattr(self, item, default)

    def __contains__(self, item):
        value = getattr(self, item, None)
        if value is None:
            return False
        field = self.__fields__[item]
        if isinstance(field, (MapField, ListField)):
            return len(value) > 0
        return True

    def __iter__(self):
        for key in self.__fields__:
            if key in self:
                yield key

    def iteritems(self):
        for key in self.__fields__:
            if key in self:
                yield key, getattr(self, key)

    def items(self):
        return self.iteritems()

    def copy(self):
        return self.__class__(**self.dump())

    def setdefault(self, key, default_value):
        if key not in self:
            setattr(self, key, default_value)

    def update(self, E=None, **F):
        # D.update([E, ]**F) -> None.  Update D from dict/iterable E and F.
        # If E present and has a .keys() method, does:     for k in E: D[k] = E[k]
        # If E present and lacks .keys() method, does:     for (k, v) in E: D[k] = v
        # In either case, this is followed by: for k in F: D[k] = F[k]
        if E is not None:
            if hasattr(E, 'keys'):
                for k in E:
                    self[k] = E[k]
            else:
                for k, v in iteritems(E):
                    self[k] = v
        for k in F:
            self[k] = F[k]


class EntityEncoder(JSONEncoder):
    # json.dumps(obj, cls=SetEncoder)
    def default(self, obj):
        if hasattr(obj, 'dump'):
            return obj.dump()
        elif hasattr(obj, '__json__'):
            return obj.__json__()
        elif hasattr(obj, 'to_json'):
            return obj.to_json()
        elif hasattr(obj, 'as_json'):
            return obj.as_json()
        elif isinstance(obj, Enum):
            return obj.value
        return JSONEncoder.default(self, obj)
