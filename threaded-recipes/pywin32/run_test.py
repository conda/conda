# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Full module list obtained from: http://timgolden.me.uk/pywin32-docs/win32_modules.html

Skipped modules:

_winxptheme: private module
wincerapi: interface to the win32 CE Remote API
"""

import platform

if platform.system() != "Windows":
    print("nothing to see here!")
elif (platform.system() == "Windows") and (platform.python_implementation() == "PyPy"):
    print("no pywin32 for pypy on windows!")
else:
    import glob
    import os

    conda_py = str(os.sys.version_info.major) + str(os.sys.version_info.minor)

    print(list(glob.glob(os.path.join(os.environ["LIBRARY_BIN"], "py*.dll"))))

    library_bin = os.environ["LIBRARY_BIN"]
    pythoncom_filename = os.path.join(library_bin, f"pythoncom{conda_py}.dll")
    pywintypes_filename = os.path.join(library_bin, f"pywintypes{conda_py}.dll")

    assert os.path.isfile(pythoncom_filename), pythoncom_filename
    assert os.path.isfile(pywintypes_filename), pywintypes_filename
