from __future__ import print_function, division, absolute_import

import json
import tarfile
from os.path import basename


def dist_fn(fn):
    if fn.endswith('.tar'):
        return fn[:-4]
    elif fn.endswith('.tar.bz2'):
        return fn[:-8]
    else:
        raise Exception('did not expect filename: %r' % fn)


class TarCheck(object):
    def __init__(self, path):
        self.t = tarfile.open(path)
        self.paths = set(m.path for m in self.t.getmembers())
        self.dist = dist_fn(basename(path))
        self.name, self.version, self.build = self.dist.rsplit('-', 2)

    def info_files(self):
        lista = [p.strip().decode('utf-8') for p in
                 self.t.extractfile('info/files').readlines()]
        seta = set(lista)
        if len(lista) != len(seta):
            raise Exception('info/files: duplicates')

        listb = [m.path for m in self.t.getmembers()
                 if not (m.path.startswith('info/') or m.isdir())]
        setb = set(listb)
        if len(listb) != len(setb):
            raise Exception('info_files: duplicate members')

        if seta == setb:
            return
        for p in sorted(seta | setb):
            if p not in seta:
                print('%r not in info/files' % p)
            if p not in setb:
                print('%r not in tarball' % p)
        raise Exception('info/files')

    def index_json(self):
        info = json.loads(self.t.extractfile('info/index.json').read().decode('utf-8'))
        for varname in 'name', 'version', 'build':
            if info[varname] != getattr(self, varname):
                raise Exception('%s: %r != %r' % (varname, info[varname],
                                                  getattr(self, varname)))
        assert isinstance(info['build_number'], int)


def check_all(path):
    x = TarCheck(path)
    x.info_files()
    x.index_json()
    x.t.close()
