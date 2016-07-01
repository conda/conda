import responses
import unittest
from conda.fetch import fetch_repodata, TmpDownload
from conda.config import DEFAULT_CHANNEL_ALIAS, remove_binstar_tokens, rc
import pytest
from os.path import exists, isfile


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
    pass