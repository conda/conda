from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import join

import conda.config as cc

from conda.builder.config import CONDA_PY, PY3K, build_prefix, build_python
from conda.builder import source


py_ver = '.'.join(str(CONDA_PY))
stdlib_dir = join(build_prefix, 'Lib' if sys.platform == 'win32' else
                                'lib/python%s' % py_ver)
sp_dir = join(stdlib_dir, 'site-packages')


def get_dict(m=None):
    d = {'CONDA_BUILD': '1'}
    d['ARCH'] = str(cc.bits)
    d['PREFIX'] = build_prefix
    d['PYTHON'] = build_python
    d['PY3K'] = str(PY3K)
    d['STDLIB_DIR'] = stdlib_dir
    d['SP_DIR'] = sp_dir
    d['SYS_PREFIX'] = sys.prefix
    d['SYS_PYTHON'] = sys.executable
    d['PY_VER'] = py_ver
    d['SRC_DIR'] = source.get_dir()

    if sys.platform == 'win32':         # -------- Windows
        d['PATH'] = (join(build_prefix, 'Library', 'bin') + ';' +
                     join(build_prefix) + ';' +
                     join(build_prefix, 'Scripts') + ';%PATH%')
        d['SCRIPTS'] = join(build_prefix, 'Scripts')
        d['LIBRARY_PREFIX'] = join(build_prefix, 'Library')
        d['LIBRARY_BIN'] = join(d['LIBRARY_PREFIX'], 'bin')
        d['LIBRARY_INC'] = join(d['LIBRARY_PREFIX'], 'include')
        d['LIBRARY_LIB'] = join(d['LIBRARY_PREFIX'], 'lib')

    else:                               # -------- Unix
        d['PATH'] = '%s/bin:%s' % (build_prefix, os.getenv('PATH'))
        d['HOME'] = os.getenv('HOME', 'UNKNOWN')
        d['LANG'] = 'en_US.UTF-8'
        d['PKG_CONFIG_PATH'] = join(build_prefix, 'lib', 'pkgconfig')

    if sys.platform == 'darwin':         # -------- OSX
        d['OSX_ARCH'] = 'i386' if cc.bits == 32 else 'x86_64'
        if cc.build_cppflags:
            d['CPPFLAGS'] = cc.build_cppflags
        d['CFLAGS'] = ('-arch %(OSX_ARCH)s' % d) if not cc.build_cflags else cc.build_cflags  #FIX ME: should this be like linux??? if an exported CFLAGS Variable exists there is no autoguess value in Linux
        d['CXXFLAGS'] = d['CFLAGS'] if not cc.build_cxxflags else cc.build_cxxflags  #FIX ME: should this be like linux???
        d['LDFLAGS'] = ('-arch %(OSX_ARCH)s' % d) if not cc.build_ldflags else cc.build_ldflags  #FIX ME: should this be like linux???
        if cc.build_fflags:
            d['FFLAGS'] = cc.build_fflags
        if cc.build_fcflags:
            d['FCFLAGS'] = cc.build_fcflags
        d['MAKEOPTS'] = '-j 1' if not cc.build_makeopts else cc.build_makeopts    #FIX ME: does that work in OSX???
        d['MACOSX_DEPLOYMENT_TARGET'] = '10.5' if not cc.build_macosx_deployment_target else cc.build_macosx_deployment_target    #FIX ME: does that work in OSX???

    elif sys.platform.startswith('linux'):      # -------- Linux
        d['LD_RUN_PATH'] = build_prefix + '/lib'
        if cc.build_cppflags:
            d['CPPFLAGS'] = cc.build_cppflags
        if cc.build_cflags:
            d['CFLAGS'] = cc.build_cflags
        if cc.build_cxxflags:
            d['CXXFLAGS'] = cc.build_cxxflags
        if cc.build_ldflags:
            d['LDFLAGS'] = cc.build_ldflags
        if cc.build_fflags:
            d['FFLAGS'] = cc.build_fflags
        if cc.build_fcflags:
            d['FCFLAGS'] = cc.build_fcflags
        d['MAKEOPTS'] = '-j 1' if not cc.build_makeopts else cc.build_makeopts
        if cc.build_chost:
            d['CHOST'] = cc.build_chost
        
    if m:
        d['PKG_NAME'] = m.name()
        d['PKG_VERSION'] = m.version()
        d['RECIPE_DIR'] = m.path

    return d


if __name__ == '__main__':
    e = get_dict()
    for k in sorted(e):
        assert isinstance(e[k], str), k
        print('%s=%s' % (k, e[k]))
