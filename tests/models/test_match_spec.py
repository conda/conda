# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger

from conda.models.dist import Dist
from conda.resolve import MatchSpec

log = getLogger(__name__)


def test_build_string():
    # regression test for #5298
    spec = MatchSpec('llvm 4.0.0 h95a1600_0')

    dist1 = Dist("local::llvm-4.0.0-h95a1600_0")
    assert spec.match(dist1)

    dist2 = Dist("local::llvm-4.0.0-heefb760_0")
    assert not spec.match(dist2)




