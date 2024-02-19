# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Script to combine test durations from all runs.

If the tests splits are looking uneven or the test suite has
siginificantly changed, update ./tools/durations/${OS}.json in the root of the
repository and pytest-split may work better.

```
$ gh run list --branch <branch>
$ gh run download --dir ./artifacts/ <databaseId>
$ python ./tools/durations/combine.py ./artifacts/
$ git add ./tools/durations/
$ git commit -m "Update test durations"
$ git push
```
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import fmean
from sys import argv

combined: dict[str, dict[str, list[float]]] = {}

durations_dir = Path(__file__).parent
artifacts_dir = Path(argv[-1]).expanduser().resolve()

# aggregate all new durations
for path in artifacts_dir.glob("**/*.json"):
    os = path.stem
    combined_os = combined.setdefault(os, {})

    data = json.loads(path.read_text())
    for key, value in data.items():
        combined_os.setdefault(key, []).append(value)

# aggregate new and old durations while discarding durations that no longer exist
for path in durations_dir.glob("**/*.json"):
    os = path.stem
    combined_os = combined.setdefault(os, {})

    data = json.loads(path.read_text())
    for key in set(combined_os).intersection(durations_dir.glob("**/*.json")):
        combined_os.setdefault(key, []).append(data[key])

# write out averaged durations
for os, combined_os in combined.items():
    (durations_dir / f"{os}.json").write_text(
        json.dumps(
            {key: fmean(values) for key, values in combined_os.items()},
            indent=4,
            sort_keys=True,
        )
        + "\n"  # include trailing newline
    )
