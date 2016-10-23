# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


def test_exports():
    import conda.exports
    assert conda.exports.PaddingError
