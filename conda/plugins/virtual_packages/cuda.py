# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import ctypes
import functools
import platform
from contextlib import suppress

from ...common.decorators import env_override
from .. import hookimpl, CondaVirtualPackage


@env_override("CONDA_OVERRIDE_CUDA", convert_empty_to_none=True)
def cuda_version():
    """
    Attempt to detect the version of CUDA present in the operating system.

    On Windows and Linux, the CUDA library is installed by the NVIDIA
    driver package, and is typically found in the standard library path,
    rather than with the CUDA SDK (which is optional for running CUDA apps).

    On macOS, the CUDA library is only installed with the CUDA SDK, and
    might not be in the library path.

    Returns: version string (e.g., '9.2') or None if CUDA is not found.
    """
    # platform-specific libcuda location
    system = platform.system()
    if system == "Darwin":
        lib_filenames = [
            "libcuda.dylib",  # check library path first
            "/usr/local/cuda/lib/libcuda.dylib",
        ]
    elif system == "Linux":
        lib_filenames = [
            "libcuda.so",  # check library path first
            "/usr/lib64/nvidia/libcuda.so",  # RHEL/Centos/Fedora
            "/usr/lib/x86_64-linux-gnu/libcuda.so",  # Ubuntu
        ]
    elif system == "Windows":
        lib_filenames = ["nvcuda.dll"]
    else:
        return None  # CUDA not available for other operating systems

    # open library
    if system == "Windows":
        dll = ctypes.windll
    else:
        dll = ctypes.cdll
    for lib_filename in lib_filenames:
        with suppress(Exception):
            libcuda = dll.LoadLibrary(lib_filename)
            break
    else:
        return None

    # Get CUDA version
    try:
        cuInit = libcuda.cuInit
        flags = ctypes.c_uint(0)
        ret = cuInit(flags)
        if ret != 0:
            return None

        cuDriverGetVersion = libcuda.cuDriverGetVersion
        version_int = ctypes.c_int(0)
        ret = cuDriverGetVersion(ctypes.byref(version_int))
        if ret != 0:
            return None

        # Convert version integer to version string
        value = version_int.value
        return "%d.%d" % (value // 1000, (value % 1000) // 10)
    except Exception:
        return None


@functools.lru_cache(maxsize=None)
def cached_cuda_version():
    """
    A cached version of the cuda detection system.
    """
    return cuda_version()


@hookimpl
def conda_virtual_packages():
    cuda_version = cached_cuda_version()
    if cuda_version is not None:
        yield CondaVirtualPackage("cuda", cuda_version, None)
