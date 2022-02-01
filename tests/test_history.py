# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from os.path import dirname
from pprint import pprint
import unittest

from conda.testing.cases import BaseTestCase
from conda.testing.decorators import skip_if_no_mock
from conda.testing.helpers import mock
from conda.testing.integration import make_temp_prefix

from conda.history import History
from conda.common.compat import text_type


class HistoryTestCase(BaseTestCase):
    def test_works_as_context_manager(self):
        h = History("/path/to/prefix")
        self.assertTrue(getattr(h, '__enter__'))
        self.assertTrue(getattr(h, '__exit__'))

    @skip_if_no_mock
    def test_calls_update_on_exit(self):
        h = History("/path/to/prefix")
        with mock.patch.object(h, 'init_log_file') as init_log_file:
            init_log_file.return_value = None
            with mock.patch.object(h, 'update') as update:
                with h:
                    self.assertEqual(0, update.call_count)
                    pass
            self.assertEqual(1, update.call_count)

    @skip_if_no_mock
    def test_returns_history_object_as_context_object(self):
        h = History("/path/to/prefix")
        with mock.patch.object(h, 'init_log_file') as init_log_file:
            init_log_file.return_value = None
            with mock.patch.object(h, 'update'):
                with h as h2:
                    self.assertEqual(h, h2)

    @skip_if_no_mock
    def test_empty_history_check_on_empty_env(self):
        with mock.patch.object(History, 'file_is_empty') as mock_file_is_empty:
            with History(make_temp_prefix()) as h:
                self.assertEqual(mock_file_is_empty.call_count, 0)
            self.assertEqual(mock_file_is_empty.call_count, 0)
            assert h.file_is_empty()
        self.assertEqual(mock_file_is_empty.call_count, 1)
        assert not h.file_is_empty()

    @skip_if_no_mock
    def test_parse_on_empty_env(self):
        with mock.patch.object(History, 'parse') as mock_parse:
            with History(make_temp_prefix(name=text_type(self.tmpdir))) as h:
                self.assertEqual(mock_parse.call_count, 0)
                self.assertEqual(len(h.parse()), 0)
        self.assertEqual(len(h.parse()), 1)


class UserRequestsTestCase(unittest.TestCase):

    h = History(dirname(__file__))
    user_requests = h.get_user_requests()

    def test_len(self):
        self.assertEqual(len(self.user_requests), 6)

    def test_0(self):
        self.assertEqual(self.user_requests[0],
                         {'cmd': ['conda', 'update', 'conda'],
                          'date': '2016-02-16 13:31:33',
                          'unlink_dists': (),
                          'link_dists': (),
                          })

    def test_last(self):
        self.assertEqual(self.user_requests[-1],
                         {'action': 'install',
                          'cmd': ['conda', 'install', 'pyflakes'],
                          'date': '2016-02-18 22:53:20',
                          'specs': ['pyflakes', 'conda', 'python 2.7*'],
                          'update_specs': ['pyflakes', 'conda', 'python 2.7*'],
                          'unlink_dists': (),
                          'link_dists': ['+pyflakes-1.0.0-py27_0'],
                          })

    def test_conda_comment_version_parsing(self):
        assert History._parse_comment_line("# conda version: 4.5.1") == {"conda_version": "4.5.1"}
        assert History._parse_comment_line("# conda version: 4.5.1rc1") == {"conda_version": "4.5.1rc1"}
        assert History._parse_comment_line("# conda version: 4.5.1dev0") == {"conda_version": "4.5.1dev0"}

    def test_specs_line_parsing_44(self):
        # New format (>=4.4)
        item = History._parse_comment_line("# update specs: [\"param[version='>=1.5.1,<2.0']\"]")
        pprint(item)
        assert item == {
            "action": "update",
            "specs": [
                "param[version='>=1.5.1,<2.0']",
            ],
            "update_specs": [
                "param[version='>=1.5.1,<2.0']",
            ],
        }

    def test_specs_line_parsing_43(self):
        # Old format (<4.4)
        item = History._parse_comment_line('# install specs: param >=1.5.1,<2.0')
        pprint(item)
        assert item == {
            'action': 'install',
            'specs': [
                'param >=1.5.1,<2.0',
            ],
            'update_specs': [
                'param >=1.5.1,<2.0',
            ],
        }

        item = History._parse_comment_line('# install specs: param >=1.5.1,<2.0,0packagename >=1.0.0,<2.0')
        pprint(item)
        assert item == {
            'action': 'install',
            'specs': [
                'param >=1.5.1,<2.0',
                '0packagename >=1.0.0,<2.0',
            ],
            'update_specs': [
                'param >=1.5.1,<2.0',
                '0packagename >=1.0.0,<2.0',
            ],
        }

        item = History._parse_comment_line('# install specs: python>=3.5.1,jupyter >=1.0.0,<2.0,matplotlib >=1.5.1,<2.0,numpy >=1.11.0,<2.0,pandas >=0.19.2,<1.0,psycopg2 >=2.6.1,<3.0,pyyaml >=3.12,<4.0,scipy >=0.17.0,<1.0')
        pprint(item)
        assert item == {
            'action': 'install',
            'specs': [
                'python>=3.5.1',
                'jupyter >=1.0.0,<2.0',
                'matplotlib >=1.5.1,<2.0',
                'numpy >=1.11.0,<2.0',
                'pandas >=0.19.2,<1.0',
                'psycopg2 >=2.6.1,<3.0',
                'pyyaml >=3.12,<4.0',
                'scipy >=0.17.0,<1.0',
            ],
            'update_specs': [
                'python>=3.5.1',
                'jupyter >=1.0.0,<2.0',
                'matplotlib >=1.5.1,<2.0',
                'numpy >=1.11.0,<2.0',
                'pandas >=0.19.2,<1.0',
                'psycopg2 >=2.6.1,<3.0',
                'pyyaml >=3.12,<4.0',
                'scipy >=0.17.0,<1.0',
            ],
        }

        item = History._parse_comment_line('# install specs: _license >=1.0.0,<2.0')
        pprint(item)
        assert item == {
            'action': 'install',
            'specs': [
                '_license >=1.0.0,<2.0',
            ],
            'update_specs': [
                '_license >=1.0.0,<2.0',
            ],
        }

        item = History._parse_comment_line('# install specs: pandas,_license >=1.0.0,<2.0')
        pprint(item)
        assert item == {
            'action': 'install',
            'specs': [
                'pandas', '_license >=1.0.0,<2.0',
            ],
            'update_specs': [
                'pandas', '_license >=1.0.0,<2.0',
            ],
        }


# behavior disabled as part of https://github.com/conda/conda/pull/8160
# def test_minimum_conda_version_error():
#     with tempdir() as prefix:
#         assert not isfile(join(prefix, 'conda-meta', 'history'))
#         mkdir_p(join(prefix, 'conda-meta'))
#         copy2(join(dirname(__file__), 'conda-meta', 'history'),
#               join(prefix, 'conda-meta', 'history'))

#         with open(join(prefix, 'conda-meta', 'history'), 'a') as fh:
#             fh.write("==> 2018-07-09 11:18:09 <==\n")
#             fh.write("# cmd: blarg\n")
#             fh.write("# conda version: 42.42.4242\n")

#         h = History(prefix)

#         with pytest.raises(CondaUpgradeError) as exc:
#             h.get_user_requests()
#         exception_string = repr(exc.value)
#         print(exception_string)
#         assert "minimum conda version: 42.42" in exception_string
#         assert "$ conda install -p" in exception_string
