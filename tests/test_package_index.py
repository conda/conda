
import unittest
import json
from os.path import dirname, join

from conda.naming import parse_package_filename
from conda.package import package
from conda.package_index import package_index
from conda.package_spec import package_spec


class test_create(unittest.TestCase):

    def setUp(self):
        path = join(dirname(__file__), 'index.json')
        with open(path) as fi:
            self.info = json.load(fi)

    def test_create_from_local(self):
        idx = package_index(self.info)

    def test_lookup_from_filename(self):
        idx = package_index(self.info)
        for pkg_filename in self.info:
            self.assertEqual(
                idx.lookup_from_filename(pkg_filename),
                package(self.info[pkg_filename])
            )

    def test_lookup_from_name(self):
        idx = package_index(self.info)

        name_count = {}
        names = set()
        for pkg_filename in self.info:
            name, version, build = parse_package_filename(pkg_filename)
            name_count[name] = name_count.get(name, 0) + 1

        for name in names:
            self.assertEqual(name_count[name], len(idx.lookup_from_name(name)))

    def test_get_deps(self):
        idx = package_index(self.info)
        self.assertEqual(
            idx.get_deps([package(self.info['bzip2-1.0.6-0.tar.bz2'])]),
            set()
        )
        self.assertEqual(
            idx.get_deps([package(self.info['conda-1.0-py27_0.tar.bz2'])], 0),
            set([
                package_spec('readline 6.2'),
                package_spec('zlib 1.2.7'),
                package_spec('python 2.7'),
                package_spec('sqlite 3.7.13'),
            ])
        )
        self.assertEqual(
            idx.get_deps([package(self.info['conda-1.0-py27_0.tar.bz2'])], 1),
            set([package_spec('python 2.7')])
        )
        self.assertEqual(
            idx.get_deps([package(self.info['conda-1.0-py27_0.tar.bz2'])], 2),
            set([
                package_spec('readline 6.2'),
                package_spec('zlib 1.2.7'),
                package_spec('python 2.7'),
                package_spec('sqlite 3.7.13'),
            ])
        )
        self.assertEqual(
            idx.get_deps([package(self.info['conda-1.0-py27_0.tar.bz2'])]),
            set([
                package_spec('readline 6.2'),
                package_spec('zlib 1.2.7'),
                package_spec('python 2.7'),
                package_spec('sqlite 3.7.13'),
            ])
        )

        def test_get_reverse_deps(self):
            idx = package_index(self.info)
            self.assertEqual(
                idx.get_reverse_deps([package(self.info['bzip2-1.0.6-0.tar.bz2'])]),
                set()
            )

    def test_get_reverse_deps(self):
        idx = package_index(self.info)
        self.assertEqual(
            idx.get_reverse_deps([package_spec('flask 0.9')]),
            set()
        )
        self.assertEqual(
            idx.get_reverse_deps([package_spec('libevent 2.0.20')], 0),
            set([
                package(self.info['gevent-0.13.7-py26_0.tar.bz2']),
                package(self.info['gevent-0.13.7-py27_0.tar.bz2']),
                package(self.info['gevent_zeromq-0.2.5-py26_0.tar.bz2']),
                package(self.info['gevent_zeromq-0.2.5-py27_0.tar.bz2']),
                package(self.info['gevent-websocket-0.3.6-py26_0.tar.bz2']),
                package(self.info['gevent-websocket-0.3.6-py27_0.tar.bz2']),
            ])
        )
        self.assertEqual(
            idx.get_reverse_deps([package_spec('libevent 2.0.20')], 1),
            set([
                package(self.info['gevent-0.13.7-py26_0.tar.bz2']),
                package(self.info['gevent-0.13.7-py27_0.tar.bz2']),
            ])
        )
        self.assertEqual(
            idx.get_reverse_deps([package_spec('libevent 2.0.20')], 2),
            set([
                package(self.info['gevent-0.13.7-py26_0.tar.bz2']),
                package(self.info['gevent-0.13.7-py27_0.tar.bz2']),
                package(self.info['gevent_zeromq-0.2.5-py26_0.tar.bz2']),
                package(self.info['gevent_zeromq-0.2.5-py27_0.tar.bz2']),
                package(self.info['gevent-websocket-0.3.6-py26_0.tar.bz2']),
                package(self.info['gevent-websocket-0.3.6-py27_0.tar.bz2']),
            ])
        )
        self.assertEqual(
            idx.get_reverse_deps([package_spec('libevent 2.0.20')]),
            set([
                package(self.info['gevent-0.13.7-py26_0.tar.bz2']),
                package(self.info['gevent-0.13.7-py27_0.tar.bz2']),
                package(self.info['gevent_zeromq-0.2.5-py26_0.tar.bz2']),
                package(self.info['gevent_zeromq-0.2.5-py27_0.tar.bz2']),
                package(self.info['gevent-websocket-0.3.6-py26_0.tar.bz2']),
                package(self.info['gevent-websocket-0.3.6-py27_0.tar.bz2']),
            ])
        )



if __name__ == '__main__':
    unittest.main()
