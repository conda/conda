import pytest
import responses
import unittest
from os.path import exists, isfile
from tempfile import mktemp

from conda.base.constants import DEFAULT_CHANNEL_ALIAS
from conda.exceptions import CondaRuntimeError, CondaHTTPError
from conda.fetch import fetch_repodata, TmpDownload, download



class TestFetchRepoData(unittest.TestCase):
    # @responses.activate
    # def test_fetchrepodata_httperror(self):
    #     with pytest.raises(CondaHTTPError) as execinfo:
    #         url = DEFAULT_CHANNEL_ALIAS
    #         user = binstar.remove_binstar_tokens(url).split(DEFAULT_CHANNEL_ALIAS)[1].split("/")[0]
    #         msg = 'Could not find anaconda.org user %s' % user
    #         filename = 'repodata.json'
    #         responses.add(responses.GET, url+filename, body='{"error": "not found"}', status=404,
    #                       content_type='application/json')
    #
    #         fetch_repodata(url)
    #         assert msg in str(execinfo), str(execinfo)

    def test_fetchrepodate_connectionerror(self):
        with pytest.raises(CondaRuntimeError) as execinfo:
            url = "http://240.0.0.0/"
            msg = "Connection error:"
            fetch_repodata(url)
            assert msg in str(execinfo)


class TestTmpDownload(unittest.TestCase):

    def test_tmpDownload(self):
        url = "https://repo.continuum.io/pkgs/free/osx-64/appscript-1.0.1-py27_0.tar.bz2"
        with TmpDownload(url) as dst:
            assert exists(dst)
            assert isfile(dst)

        msg = "Rock and Roll Never Die"
        with TmpDownload(msg) as result:
            assert result == msg


class TestDownload(unittest.TestCase):

    def test_download_connectionerror(self):
        with pytest.raises(CondaRuntimeError) as execinfo:
            url = "http://240.0.0.0/"
            msg = "Connection error:"
            download(url, mktemp())
            assert msg in str(execinfo)

    @responses.activate
    def test_download_httperror(self):
        with pytest.raises(CondaRuntimeError) as execinfo:
            url = DEFAULT_CHANNEL_ALIAS
            msg = "HTTPError:"
            responses.add(responses.GET, url, body='{"error": "not found"}', status=404,
                          content_type='application/json')
            download(url, mktemp())
            assert msg in str(execinfo)