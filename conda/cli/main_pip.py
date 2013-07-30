# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import sys


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('pip')
    p.add_argument('packages', nargs='*')
    p.set_defaults(func=execute)


def execute(args, parser):
    sys.exit("""ERROR:
The "conda pip" command has been removed from conda version 1.8 for the
following reasons:
  * users get the wrong impression that you *must* use conda pip (instead
    of simply pip) when using Anaconda
  * there should only be one preferred way to build packages, and that is
    the conda build command
  * the command did too many things at once, i.e. build a package and
    then also install it
  * the command is Python centric, whereas conda (from a package management
    perspective) is Python agnostic
  * packages created with conda pip are not robust, i.e. they will maybe
    not work on other peoples systems

In short:
  * use "conda build" is you want to build a conda package
  * use "pip" if you want to install something

""")
