import responses
import unittest
from conda.fetch import fetch_repodata, TmpDownload, download
from conda.config import DEFAULT_CHANNEL_ALIAS, remove_binstar_tokens
import pytest
from os.path import exists, isfile
from tempfile import mktemp

class TestFetchRepoData(unittest.TestCase):
    @responses.activate
    def test_fetchrepodata_httperror(self):
        with pytest.raises(RuntimeError) as execinfo:
            url = DEFAULT_CHANNEL_ALIAS
            user = remove_binstar_tokens(url).split(DEFAULT_CHANNEL_ALIAS)[1].split("/")[0]
            msg = 'Could not find anaconda.org user %s' % user
            filename = 'repodata.json'
            responses.add(responses.GET, url+filename, body='{"error": "not found"}', status=404,
                          content_type='application/json')

            fetch_repodata(url)
            assert msg in str(execinfo), str(execinfo)

        with pytest.raises(RuntimeError):
            url = "http://www.google.com/noarch/'"
            msg = 'Could not find URL: %s' % remove_binstar_tokens(url)
            filename = 'repodata.json'
            responses.add(responses.GET, url+filename, body='{"error": "not found"}', status=403,
                          content_type='application/json')

            res = fetch_repodata(url)
            assert not res

    def test_fetchrepodate_connectionerror(self):
        with pytest.raises(RuntimeError) as execinfo:
            url = "http://10.0.0.0/"
            msg = "Connection error:"
            filename = 'repodata.json'
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
        with pytest.raises(RuntimeError) as execinfo:
            url = "http://10.0.0.0/"
            msg = "Connection error:"
            download(url, mktemp())
            assert msg in str(execinfo)

    @responses.activate
    def test_download_httperror(self):
        with pytest.raises(RuntimeError) as execinfo:
            url = "http://www.google.com/noarch"
            msg = "HTTPError:"
            responses.add(responses.GET, url, body='{"error": "not found"}', status=404,
                          content_type='application/json')
            download(url, mktemp())
            assert msg in str(execinfo)