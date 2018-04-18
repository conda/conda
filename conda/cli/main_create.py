# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os.path import isdir

from .common import confirm_yn
from .install import install
from ..base.context import context
from ..common.path import paths_equal
from ..exceptions import CondaValueError
from ..gateways.disk.delete import delete_trash, rm_rf
from ..gateways.disk.test import is_conda_environment

log = getLogger(__name__)


def execute(args, parser):
    if is_conda_environment(context.target_prefix):
        if paths_equal(context.target_prefix, context.root_prefix):
            raise CondaValueError("The target prefix is the base prefix. Aborting.")
        confirm_yn("WARNING: A conda environment already exists at '%s'\n"
                   "Removing existing environment" % context.target_prefix,
                   default='no',
                   dry_run=False)
        log.info("Removing existing environment %s", context.target_prefix)
        rm_rf(context.target_prefix)
    elif isdir(context.target_prefix):
        confirm_yn("WARNING: A directory already exists at the target location '%s'\n"
                   "but it is not a conda environment.\n"
                   "Continue creating environment" % context.target_prefix,
                   default='no',
                   dry_run=False)

    install(args, parser, 'create')
    delete_trash()
