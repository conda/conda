# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from logging import getLogger
from os.path import isdir

from ..base.context import context
from ..common.path import paths_equal
from ..exceptions import CondaValueError
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.test import is_conda_environment
from ..notices import notices
from .common import confirm_yn
from .install import install

log = getLogger(__name__)


@notices
def execute(args, parser):
    if is_conda_environment(context.target_prefix):
        if paths_equal(context.target_prefix, context.root_prefix):
            raise CondaValueError("The target prefix is the base prefix. Aborting.")
        if context.dry_run:
            # Taking the "easy" way out, rather than trying to fake removing
            # the existing environment before creating a new one.
            raise CondaValueError(
                "Cannot `create --dry-run` with an existing conda environment"
            )
        confirm_yn(
            "WARNING: A conda environment already exists at '%s'\n"
            "Remove existing environment" % context.target_prefix,
            default="no",
            dry_run=False,
        )
        log.info("Removing existing environment %s", context.target_prefix)
        rm_rf(context.target_prefix)
    elif isdir(context.target_prefix):
        confirm_yn(
            "WARNING: A directory already exists at the target location '%s'\n"
            "but it is not a conda environment.\n"
            "Continue creating environment" % context.target_prefix,
            default="no",
            dry_run=False,
        )

    install(args, parser, "create")
