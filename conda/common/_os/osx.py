# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import platform
from subprocess import check_output


def copy_acl(source_fd: int, destination_fd: int) -> None:
    """Copy a file's access-control list between open file descriptors."""
    from ctypes import CDLL, c_int, c_uint32, c_void_p, get_errno

    fcopyfile = CDLL(None, use_errno=True).fcopyfile
    fcopyfile.argtypes = (c_int, c_int, c_void_p, c_uint32)
    fcopyfile.restype = c_int

    copyfile_acl = 1
    if fcopyfile(source_fd, destination_fd, None, copyfile_acl) != 0:
        error = get_errno()
        raise OSError(error, "Could not copy file ACL")


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
