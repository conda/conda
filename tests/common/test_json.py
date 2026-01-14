# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for conda.common.serialize.json module."""

from __future__ import annotations

import json

from frozendict import frozendict

from conda.common.serialize.json import CondaJSONEncoder, dumps


def test_condajsonencoder_serialises_frozendicts():
    frozen = frozendict({"name": "test-package", "version": "1.0.0"})
    result = json.dumps(frozen, cls=CondaJSONEncoder)

    assert json.loads(result) == {"name": "test-package", "version": "1.0.0"}

    data = {
        "actions": {
            "UNLINK": [
                frozendict({"name": "package1"}),
                frozendict({"name": "package2"}),
            ]
        }
    }
    result = json.dumps(data, cls=CondaJSONEncoder)
    parsed = json.loads(result)

    assert parsed["actions"]["UNLINK"][0]["name"] == "package1"
    assert parsed["actions"]["UNLINK"][1]["name"] == "package2"


def test_condajsonencoder_with_dumps():
    frozen = frozendict({"key": "value"})
    result = dumps(frozen)
    assert json.loads(result) == {"key": "value"}
