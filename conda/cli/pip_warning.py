# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from .._vendor.auxlib.ish import dals


def main():
    from ..base.constants import CONDA_HOMEPAGE_URL
    message = dals("""
    ERROR: The install method you used for conda--probably either `pip install conda`
    or `easy_install conda`--is not compatible with using conda as an application.
    If your intention is to install conda as a standalone application, currently
    supported install methods include the Anaconda installer and the miniconda
    installer.  You can download the miniconda installer from
    %s/miniconda.html.
    """) % CONDA_HOMEPAGE_URL
    print(message, file=sys.stderr)
    sys.exit(1)
