# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from logging import getLogger

log = getLogger(__name__)

from conda._vendor.auxlib.compat import (iteritems, with_metaclass, itervalues,  # NOQA
                                         string_types, primitive_types, text_type, odict,  # NOQA
                                         StringIO, isiterable)  # NOQA
