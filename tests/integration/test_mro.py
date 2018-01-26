# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger
from os.path import join
from uuid import uuid4

from coverage.annotate import os
import pytest

from conda._vendor.auxlib.ish import dals
from conda.activate import Activator
from conda.base.context import reset_context
from conda.common.compat import string_types
from conda.common.io import env_var
from conda.common.path import get_python_short_path
from conda.core.linked_data import PrefixData
from conda.gateways.subprocess import subprocess_call
from conda.models.match_spec import MatchSpec
from ..test_create import make_temp_env, run_command, Commands

log = getLogger(__name__)


def spec_is_installed(prefix, match_spec_or_package_ref):
    if isinstance(match_spec_or_package_ref, string_types):
        match_spec_or_package_ref = MatchSpec(match_spec_or_package_ref)
    matches = tuple(PrefixData(prefix).query(match_spec_or_package_ref))
    assert len(matches) <= 1
    return matches[0] if matches else False


def run_rpy2_test(prefix):
    script = dals("""
    from rpy2.robjects.packages import importr, data
    import numpy
    datasets = importr("datasets")
    ostatus = data(datasets).fetch("occupationalStatus")["occupationalStatus"]
    ostatus_np = numpy.array(ostatus)
    print(ostatus)
    print(ostatus_np)
    assert ostatus[0] == ostatus_np[0, 0] == 50
    assert (ostatus_np == ostatus).all()
    """)
    script = '; '.join(script.strip().splitlines())
    python_exe = join(prefix, get_python_short_path())
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join(Activator._get_path_dirs(prefix)) + os.pathsep + env['PATH']
    result = subprocess_call("'%s' -c '%s'" % (python_exe, script), env=env, raise_on_error=False)
    assert result.rc == 0
    assert not result.stderr
    return result.stdout


@pytest.mark.skipif(not os.getenv("QA", None), reason="Only run for manual QA.")
def test_mro_for_existing_r_env():
    with make_temp_env(name=str(uuid4())[:8]) as prefix:  # no space or unicode in path

        # 1. Start with pkgs/r::r
        # 2. Make sure r-base from pkgs/r is installed, make sure mro-base is not installed
        default_channels = (
            'https://repo.continuum.io/pkgs/main',
            'https://repo.continuum.io/pkgs/free',
            'https://repo.continuum.io/pkgs/r',
        )
        with env_var("CONDA_DEFAULT_CHANNELS", ','.join(default_channels), reset_context):
            run_command(Commands.INSTALL, prefix, 'r')
            assert spec_is_installed(prefix, "pkgs/r::r-base")
            assert not spec_is_installed(prefix, "mro-base")

        # 3. Add pkgs/mro into defaults
        default_channels = (
            'https://repo.continuum.io/pkgs/main',
            'https://repo.continuum.io/pkgs/free',
            'https://repo.continuum.io/pkgs/mro',
            'https://repo.continuum.io/pkgs/r',
        )
        with env_var("CONDA_DEFAULT_CHANNELS", ','.join(default_channels), reset_context):
            # 4. Install r-mime=0.4
            #    Make sure installed package is from pkgs/r
            #    Make sure no packages are from pkgs/mro
            run_command(Commands.INSTALL, prefix, 'r-mime=0.4')
            assert spec_is_installed(prefix, "pkgs/r::r-mime=0.4")
            assert spec_is_installed(prefix, "pkgs/r::r-base")
            assert not spec_is_installed(prefix, "mro-base")
            assert not spec_is_installed(prefix, "pkgs/mro::*")

            # 5. Update r-mime. Make sure installed package is from pkgs/r and not r-mime=0.4
            run_command(Commands.UPDATE, prefix, 'r-mime')
            assert not spec_is_installed(prefix, "pkgs/r::r-mime=0.4")
            assert spec_is_installed(prefix, "pkgs/r::r-mime")
            assert spec_is_installed(prefix, "pkgs/r::r-base")
            assert not spec_is_installed(prefix, "mro-base")

            # 6. Install rpy2 numpy python=2
            run_command(Commands.INSTALL, prefix, 'rpy2 numpy python=2')
            assert spec_is_installed(prefix, "python=2")
            assert spec_is_installed(prefix, "pkgs/r::r-base")
            assert not spec_is_installed(prefix, "mro-base")
            run_rpy2_test(prefix)

            # 7. conda update --all
            # TODO Make sure mro-base is installed, and all r packages are from pkgs/mro
            run_command(Commands.UPDATE, prefix, '--all')
            assert spec_is_installed(prefix, "python=2")
            assert spec_is_installed(prefix, "pkgs/r::r-base")
            assert not spec_is_installed(prefix, "mro-base")
            run_rpy2_test(prefix)

            # 8. conda update python
            run_command(Commands.UPDATE, prefix, 'python')
            assert not spec_is_installed(prefix, "python=2")
            assert spec_is_installed(prefix, "python=3")
            assert spec_is_installed(prefix, "pkgs/r::r-base")
            assert not spec_is_installed(prefix, "mro-base")
            run_rpy2_test(prefix)


