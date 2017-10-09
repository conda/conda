# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger

from conda.models.index_record import IndexRecord

log = getLogger(__name__)


def test_index_record_timestamp():
    # regression test for #6096
    ts = 1507565728
    new_ts = ts * 1000
    rec = IndexRecord(
        name='test-package',
        version='1.2.3',
        build='2',
        build_number=2,
        timestamp=ts
    )
    assert rec.timestamp == new_ts
    assert rec.dump()['timestamp'] == new_ts

    ts = 1507565728999
    new_ts = ts
    rec = IndexRecord(
        name='test-package',
        version='1.2.3',
        build='2',
        build_number=2,
        timestamp=ts
    )
    assert rec.timestamp == new_ts
    assert rec.dump()['timestamp'] == new_ts

