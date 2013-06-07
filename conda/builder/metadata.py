import re
import os
from collections import defaultdict
from os.path import isdir, isfile, join

from conda.utils import memoized
import conda.config as config

import yaml


ANA_PY = int(os.getenv('ANA_PY'), config.default_python)
ANA_NPY = int(os.getenv('ANA_NPY'), config.default_numpy)


def ns_cfg():
    plat = config.platform
    py = ANA_PY
    np = ANA_NPY
    for x in py, np:
        assert isinstance(x, int), x
    return dict(
        linux = plat.startswith('linux-'),
        linux32 = bool(plat == 'linux-32'),
        linux64 = bool(plat == 'linux-64'),
        armv6 = bool(plat == 'linux-armv6l'),
        osx = plat.startswith('osx-'),
        unix = plat.startswith(('linux-', 'osx-')),
        win = plat.startswith('win-'),
        win32 = bool(plat == 'win-32'),
        win64 = bool(plat == 'win-64'),
        py = py,
        py3k = bool(30 <= py < 40),
        py2k = bool(20 <= py < 30),
        py26 = bool(py == 26),
        py27 = bool(py == 27),
        py33 = bool(py == 33),
        np = np,
    )


sel_pat = re.compile(r'(.+?)\s*\[(.+)\]$')
def select_lines(data, namespace):
    lines = []
    for line in data.splitlines():
        line = line.rstrip()
        m = sel_pat.match(line)
        if m:
            cond = m.group(2)
            if eval(cond, namespace, {}):
                lines.append(m.group(1))
            continue
        lines.append(line)
    return '\n'.join(lines) + '\n'


@memoized
def yamlize(data):
    return yaml.load(data)


def parse(data):
    data = select_lines(data, ns_cfg())
    res = yamlize(data)
    # ensure the result is a dict
    if res is None:
        res = {}
    # ensure those are lists
    for fieldname in ('source/patches',
                      'build/entry_points',
                      'build/features', 'build/track_features',
                      'requirements/build', 'requirements/run',
                      'requirements/conflicts', 'test/requires',
                      'test/files', 'test/commands', 'test/imports'):
        section, key = fieldname.split('/')
        if res.get(section) is None:
            res[section] = {}
        if res[section].get(key, None) is None:
            res[section][key] = []
    # ensure those are strings
    for fieldname in ('source/git_tag', 'source/git_branch', 'source/md5'):
        section, key = fieldname.split('/')
        if res.get(section) is None:
            res[section] = {}
        res[section][key] = str(res[section].get(key, ''))
    return res


def name_pkg(pkg):
    return pkg.rsplit('-', 1)[0]


class MetaData(object):

    def __init__(self, path):
        assert isdir(path)
        self.path = path
        meta_path = join(path, 'meta.yaml')
        self.meta = parse(open(meta_path).read())

    def get_value(self, field, default=None):
        section, key = field.split('/')
        return self.meta.get(section, {}).get(key, default)

    def build_number(self):
        return int(self.get_value('build/number', 0))

    def run_requires(self, typ):
        return self.get_value('requirements/run')

    def build_id(self):
        res = []
        for name, s in (('numpy', 'np'), ('python', 'py')):
            for p in self.run_requires(pkg):
                n, v = p.rsplit('-', 1)
                if n == name:
                    res.append(s + v[0] + v[2])
                    break
        if res:
            res.append('_')
        res.append('%s%d' % (self.get_value(pkg, 'build/channel', ''),
                             self.build_number(pkg)))
        return ''.join(res)

    def canonical_name(self, pkg):
        return '%s-%s' % (pkg, self.build_id(pkg))


if __name__ == '__main__':
    pass

