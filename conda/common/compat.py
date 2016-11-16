# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from .._vendor.auxlib.compat import (iteritems, with_metaclass, itervalues,  # NOQA
                                     string_types, primitive_types, text_type, odict,  # NOQA
                                     StringIO, isiterable)  # NOQA
from ..base.constants import UTF8
from ..compat import *  # NOQA

log = getLogger(__name__)


def ensure_binary(value):
    return value.encode(UTF8) if hasattr(value, 'encode') else value


def ensure_text_type(value):
    return value.decode(UTF8) if hasattr(value, 'decode') else value
