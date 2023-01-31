#!/usr/bin/env python
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path

count = 0
combined = {}
for path in Path(".").glob("*/.test_durations"):
    data = json.loads(path.read_text())
    for key in data:
        if key in combined:
            existing = combined[key]
        else:
            existing = data[key]
        combined[key] = (existing + data[key]) / 2.0
    count += 1

print(f"Read {count} .test_durations")

Path("combined_durations.json").write_text(json.dumps(combined, indent=2, sort_keys=True))
