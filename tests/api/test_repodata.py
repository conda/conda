# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from conda.repodata import RepoData  # the interface to be tested
import conda.core.repodata as _impl  # the backend to be mocked
import conda.core.index as _index    # the old interface to be tested

from unittest import TestCase
import pytest
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

class UnitTests(TestCase):
    """Test RepoData API directly and make sure the appropriate backend functions are used."""
    
    def test_load(self):

        # simply test that the `sync()` call correctly forwards to the
        # underlying `fetch_repodata()` call.
        with patch('conda.core.repodata.fetch_repodata') as fetch_repodata:
            fetch_repodata.return_value = {'a':'A'}
            repodata = RepoData('url', 'name', 1)
            repodata.load()
            fetch_repodata.assert_called_once()
            assert fetch_repodata.call_args[0] == ('url', 'name', 1)
            assert repodata.index == {'a':'A'}

    def test_load_all(self):

        # simply test that the `sync()` call correctly forwards to the
        # underlying `fetch_repodata()` call.
        with patch('conda.core.repodata.fetch_repodata') as fetch_repodata:
            RepoData.enable('url1', 'name1', 1)
            RepoData.enable('url2', 'name2', 2)
            RepoData.enable('url3', 'name3', 3)
            RepoData.load_all(False)
            assert fetch_repodata.call_count == 3
            # Extract the explicit args...
            call_args_list = [a[0] for a in fetch_repodata.call_args_list]
            # ...and validate them (we don't know the order of the calls !)
            assert ('url1', 'name1', 1) in call_args_list
            assert ('url2', 'name2', 2) in call_args_list
            assert ('url3', 'name3', 3) in call_args_list

    def test_storage(self):
        # test 'persist' and 'restore'

        # make sure a given state is correctly persisted (and restored)
        pass

    def test_query(self):
        # test 'contains' and 'query'

        # make sure basic query operations are supported
        pass

    def test_add(self):
        # test 'validate', 'add', and 'remove'

        # make sure addition and removal work
        pass
        
class IntegratedTests(TestCase):
    """Test the RepoData API as executed through the old API."""

    def test_get_index(self):

        with patch('conda.core.repodata.fetch_repodata') as fetch_repodata:

            linux64 = 'linux-64'
            index = _index.get_index(platform=linux64)
            fetch_repodata.assert_called()
