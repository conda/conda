# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os.path import join
import sys

from . import CONDA_PACKAGE_ROOT

log = getLogger(__name__)


class Hook(object):

    def __init__(self, prefix, auto_activate):
        self.prefix = prefix
        self.auto_activate = auto_activate

    @property
    def conda_exe(self):
        if on_win:
            return join(self.prefix, 'Scripts', 'conda.exe')
        else:
            return join(self.prefix, 'bin', 'conda')

    def posix(self):
        source_path = join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'profile.d', 'conda.sh')
        builder = []

        if on_win:
            builder.append('_CONDA_EXE="$(cygpath \'%s\'")' % self.conda_exe)
        else:
            builder.append('_CONDA_EXE="%s"' % self.conda_exe)

        with open(source_path) as fsrc:
            builder.append(fsrc.read())

        if self.auto_activate:
            builder.append("conda activate base\n")

        return "\n".join(builder)

    def csh(self):
        source_path = join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'profile.d', 'conda.csh')
        builder = []

        if on_win:
            builder.append('setenv _CONDA_ROOT `cygpath %s`' % self.prefix)
            builder.append('setenv _CONDA_EXE `cygpath %s`' % self.conda_exe)
        else:
            builder.append('setenv _CONDA_ROOT "%s"' % self.prefix)
            builder.append('setenv _CONDA_EXE "%s"' % self.conda_exe)

        with open(source_path) as fsrc:
            builder.append(fsrc.read())

        if self.auto_activate:
            builder.append("conda activate base\n")

        return "\n".join(builder)

    def fish(self):
        source_path = join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'fish', 'conf.d', 'conda.fish')
        builder = []

        if on_win:
            builder.append('set _CONDA_ROOT (cygpath %s)' % self.prefix)
            builder.append('set _CONDA_EXE (cygpath %s)' % self.conda_exe)
        else:
            builder.append('set _CONDA_ROOT "%s"' % self.prefix)
            builder.append('set _CONDA_EXE "%s"' % self.conda_exe)

        with open(source_path) as fsrc:
            builder.append(fsrc.read())

        if self.auto_activate:
            builder.append("conda activate base\n")

        return "\n".join(builder)

    def xsh(self):
        source_path = join(CONDA_PACKAGE_ROOT, 'shell', 'conda.xsh')
        builder = []

        builder.append('_CONDA_EXE="%s"' % self.conda_exe)

        with open(source_path) as fsrc:
            builder.append(fsrc.read())

        if self.auto_activate:
            builder.append("conda activate base\n")

        return "\n".join(builder)


on_win = bool(sys.platform == "win32")



"""

eval "$(conda hook posix)"
posix, sh, bash, zsh, dash, ash


eval (conda hook fish)


eval `conda hook csh`
csh, tcsh

TODO: xsh

"""


def main():
    argv = sys.argv
    assert len(argv) == 3
    shell_name = argv[2]

    shell_map = {
        'posix': 'posix',
        'sh': 'posix',
        'bash': 'posix',
        'dash': 'posix',
        'ash': 'posix',
        'zsh': 'posix',
        'csh': 'csh',
        'tcsh': 'csh',
        'cmd.exe': 'cmd.exe',
        'cmd': 'cmd.exe',
        'fish': 'fish',
        'xonsh': 'xonsh',
    }

    from .base.context import context
    context.__init__()  # On import, context does not include SEARCH_PATH. This line fixes that.
    hook = Hook(context.conda_prefix, context.auto_activate_base)
    print(getattr(hook, shell_map[shell_name])())
    return 0


if __name__ == "__main__":
    sys.exit(main())
