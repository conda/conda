# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import platform
from subprocess import check_output


def mac_ver() -> str:
    """
    Returns macOS version, without compatibility modes for 11.x.
    https://github.com/conda/conda/issues/13832
    If Python was compiled against macOS <=10.15, we might get 10.16 instead of 11.0.
    For these cases, we must set SYSTEM_VERSION_COMPAT=0 and call sw_vers directly.
    """
    distribution_version = platform.mac_ver()[0]
    if distribution_version == "10.16":
        return check_output(
            ["/usr/bin/sw_vers", "-productVersion"],
            env={"SYSTEM_VERSION_COMPAT": "0"},
            text=True,
        ).strip()
    return distribution_version
