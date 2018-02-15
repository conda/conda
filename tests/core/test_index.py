# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from unittest import TestCase

import pytest

from conda.base.constants import DEFAULT_CHANNELS
from conda.base.context import reset_context, context
from conda.common.compat import iteritems
from conda.common.io import env_var
from conda.core.index import get_index, check_whitelist, get_reduced_index
from conda.exceptions import OperationNotAllowed
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec
from tests.core.test_repodata import platform_in_record

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

log = getLogger(__name__)


def test_check_whitelist():
    # get_index(channel_urls=(), prepend=True, platform=None, use_local=False, use_cache=False, unknown=None, prefix=None)
    whitelist = (
        'defaults',
        'conda-forge',
        'https://beta.conda.anaconda.org/conda-test'
    )
    with env_var('CONDA_WHITELIST_CHANNELS', ','.join(whitelist), reset_context):
        with pytest.raises(OperationNotAllowed):
            get_index(("conda-canary",))

        with pytest.raises(OperationNotAllowed):
            get_index(("https://repo.anaconda.com/pkgs/denied",))

        check_whitelist(("defaults",))
        check_whitelist((DEFAULT_CHANNELS[0], DEFAULT_CHANNELS[1]))
        check_whitelist(("https://conda.anaconda.org/conda-forge/linux-64",))

    check_whitelist(("conda-canary",))



@pytest.mark.integration
class GetIndexIntegrationTests(TestCase):

    def test_get_index_linux64_platform(self):
        linux64 = 'linux-64'
        index = get_index(platform=linux64)
        for dist, record in iteritems(index):
            assert platform_in_record(linux64, record), (linux64, record.url)

    def test_get_index_osx64_platform(self):
        osx64 = 'osx-64'
        index = get_index(platform=osx64)
        for dist, record in iteritems(index):
            assert platform_in_record(osx64, record), (osx64, record.url)

    def test_get_index_win64_platform(self):
        win64 = 'win-64'
        index = get_index(platform=win64)
        for dist, record in iteritems(index):
            assert platform_in_record(win64, record), (win64, record.url)


@pytest.mark.integration
class ReducedIndexTests(TestCase):

    def test_basic_get_reduced_index(self):
        get_reduced_index(None, (Channel('defaults'), Channel('conda-test')), context.subdirs,
                          (MatchSpec('flask'), ))
