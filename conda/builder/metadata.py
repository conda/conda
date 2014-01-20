from __future__ import print_function, division, absolute_import

import re
import sys
from os.path import isdir, isfile, join

from conda.compat import iteritems
from conda.utils import memoized, md5_file
import conda.config as config
from conda.resolve import MatchSpec

from conda.builder.config import CONDA_PY, CONDA_NPY



def ns_cfg():
    # Remember to update the docs of any of this changes
    plat = config.subdir
    py = CONDA_PY
    np = CONDA_NPY
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
    for i, line in enumerate(data.splitlines()):
        line = line.rstrip()
        m = sel_pat.match(line)
        if m:
            cond = m.group(2)
            try:
                if eval(cond, namespace, {}):
                    lines.append(m.group(1))
            except:
                sys.exit('''\
Error: Invalid selector in meta.yaml line %d:
%s
''' % (i + 1, line))
                sys.exit(1)
            continue
        lines.append(line)
    return '\n'.join(lines) + '\n'


@memoized
def yamlize(data):
    try:
        import yaml
    except ImportError:
        sys.exit('Error: could not import yaml (required to read meta.yaml '
                 'files of conda recipes)')

    return yaml.load(data)


def parse(data):
    data = select_lines(data, ns_cfg())
    res = yamlize(data)
    # ensure the result is a dict
    if res is None:
        res = {}
    # ensure those are lists
    for field in ('source/patches',
                  'build/entry_points',
                  'build/features', 'build/track_features',
                  'requirements/build', 'requirements/run',
                  'requirements/conflicts', 'test/requires',
                  'test/files', 'test/commands', 'test/imports'):
        section, key = field.split('/')
        if res.get(section) is None:
            res[section] = {}
        if res[section].get(key, None) is None:
            res[section][key] = []
    # ensure those are strings
    for field in ('package/version', 'build/string', 'source/svn_rev',
                  'source/git_tag', 'source/git_branch', 'source/md5'):
        section, key = field.split('/')
        if res.get(section) is None:
            res[section] = {}
        res[section][key] = str(res[section].get(key, ''))
    return res


FIELDS = {
    'package': ['name', 'version'],
    'source': ['fn', 'url', 'md5', 'sha1',
               'git_url', 'git_tag', 'git_branch',
               'hg_url', 'hg_tag',
               'svn_url', 'svn_rev', 'svn_ignore_externals',
               'patches'],
    'build': ['number', 'string', 'entry_points', 'osx_is_app', 'rm_py',
              'features', 'track_features', 'preserve_egg_dir',
              'no_softlink'],
    'requirements': ['build', 'run', 'conflicts'],
    'app': ['entry', 'icon', 'summary', 'type', 'cli_opts'],
    'test': ['requires', 'commands', 'files', 'imports'],
    'about': ['home', 'license', 'summary'],
}

def check_bad_chrs(s, field):
    bad_chrs = '=!@#$%^&*:;"\'\\|<>?/ '
    if field in ('package/version', 'build/string'):
        bad_chrs += '-'
    for c in bad_chrs:
        if c in s:
            sys.exit("Error: bad character '%s' in %s: %s" % (c, field, s))


class MetaData(object):

    def __init__(self, path):
        assert isdir(path)
        self.path = path
        self.meta_path = join(path, 'meta.yaml')
        if not isfile(self.meta_path):
            sys.exit("Error: no such file: %s" % self.meta_path)
        self.meta = parse(open(self.meta_path).read())

    def get_section(self, section):
        return self.meta.get(section, {})

    def get_value(self, field, default=None):
        section, key = field.split('/')
        return self.get_section(section).get(key, default)

    def check_fields(self):
        for section, submeta in iteritems(self.meta):
            if section not in FIELDS:
                sys.exit("Error: unknown section: %s" % section)
            for key in submeta:
                if key not in FIELDS[section]:
                    sys.exit("Error: in section %r: unknown key %r" %
                             (section, key))

    def name(self):
        res = self.get_value('package/name')
        if not res:
            sys.exit('Error: package/name missing in: %r' % self.meta_path)
        res = str(res)
        if res != res.lower():
            sys.exit('Error: package/name must be lowercase, got: %r' % res)
        check_bad_chrs(res, 'package/name')
        return res

    def version(self):
        res = self.get_value('package/version')
        check_bad_chrs(res, 'package/version')
        return res

    def build_number(self):
        return int(self.get_value('build/number', 0))

    def ms_depends(self, typ='run'):
        res = []
        for spec in self.get_value('requirements/' + typ):
            try:
                ms = MatchSpec(spec)
            except AssertionError:
                raise RuntimeError("Invalid package specification: %r" % spec)
            for name, ver in [('python', CONDA_PY), ('numpy', CONDA_NPY)]:
                if ms.name == name:
                    if ms.strictness != 1:
                        sys.exit("""Error:
    You cannot specify a version for package '%s' in the requirements.
    Please use the environment variables CONDA_PY or CONDA_NPY.
""" % name)
                    ms = MatchSpec('%s %s*' % (name, '.'.join(str(ver))))
            res.append(ms)
        return res

    def build_id(self):
        ret = self.get_value('build/string')
        if ret:
            check_bad_chrs(ret, 'build/string')
            return ret
        res = []
        for name, s in (('numpy', 'np'), ('python', 'py')):
            for ms in self.ms_depends():
                if ms.name == name:
                    v = ms.spec.split()[1]
                    res.append(s + v[0] + v[2])
                    break
        if res:
            res.append('_')
        res.append('%d' % self.build_number())
        return ''.join(res)

    def dist(self):
        return '%s-%s-%s' % (self.name(), self.version(), self.build_id())

    def is_app(self):
        return bool(self.get_value('app/entry'))

    def app_meta(self):
        d = {'type': 'app'}
        if self.get_value('app/icon'):
            d['icon'] = '%s.png' % md5_file(join(
                    self.path, self.get_value('app/icon')))

        for field, key in [('app/entry', 'app_entry'),
                           ('app/type', 'app_type'),
                           ('app/cli_opts', 'app_cli_opts'),
                           ('app/summary', 'summary')]:
            value = self.get_value(field)
            if value:
                d[key] = value
        return d

    def info_index(self):
        d = dict(
            name = self.name(),
            version = self.version(),
            build = self.build_id(),
            build_number = self.build_number(),
            platform = config.platform,
            arch = config.arch_name,
            depends = sorted(ms.spec for ms in self.ms_depends())
        )
        if self.is_app():
            d.update(self.app_meta())
        return d


if __name__ == '__main__':
    from pprint import pprint
    from os.path import expanduser

    m = MetaData(expanduser('~/conda-recipes/pycosat'))
    pprint(m.info_index())
