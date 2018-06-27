# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.common.compat import on_win


def test_exports():
    import conda.exports
    assert conda.exports.PaddingError


def test_conda_subprocess():
    import os
    from subprocess import Popen, PIPE
    import conda

    p = Popen(['echo', '"%s"' % conda.__version__], env=os.environ, stdout=PIPE, stderr=PIPE, 
              shell=on_win)
    stdout, stderr = p.communicate()
    rc = p.returncode
    if rc != 0:
        raise CalledProcessError(rc, command, "stdout: {0}\nstderr: {1}".format(stdout, stderr))
