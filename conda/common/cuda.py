# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

def cuda_detect():
    '''Attempt to detect the version of CUDA present in the operating system.

    On Windows and Linux, the CUDA library is installed by the NVIDIA
    driver package, and is typically found in the standard library path,
    rather than with the CUDA SDK (which is optional for running CUDA apps).

    On macOS, the CUDA library is only installed with the CUDA SDK, and
    might not be in the library path.

    Returns: version string (Ex: '9.2') or None if CUDA not found.
    '''
    # platform specific libcuda location
    import platform
    system = platform.system()
    if system == 'Darwin':
        lib_filenames = [
            'libcuda.dylib',  # check library path first
            '/usr/local/cuda/lib/libcuda.dylib'
        ]
    elif system == 'Linux':
        lib_filenames = [
            'libcuda.so',  # check library path first
            '/usr/lib64/nvidia/libcuda.so',  # Redhat/CentOS/Fedora
            '/usr/lib/x86_64-linux-gnu/libcuda.so',  # Ubuntu
            '/usr/lib/wsl/lib/libcuda.so',  # WSL
        ]
    elif system == 'Windows':
        lib_filenames = ['nvcuda.dll']
    else:
        return None  # CUDA not available for other operating systems

    # open library
    import ctypes
    if system == 'Windows':
        dll = ctypes.windll
    else:
        dll = ctypes.cdll
    libcuda = None
    for lib_filename in lib_filenames:
        try:
            libcuda = dll.LoadLibrary(lib_filename)
            break
        except:
            pass
    if libcuda is None:
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
        return '%d.%d' % (value // 1000, (value % 1000) // 10)
    except:
        return None
