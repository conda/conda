# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.common.constants import NULL
from logging import getLogger

log = getLogger(__name__)


def test_null_is_falsey():
    assert not NULL
