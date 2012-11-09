from os import getenv, listdir
from os.path import abspath, exists, expanduser, isdir, join
import logging
import platform
import sys

from conda import __version__
from environment import environment
from install import available


log = logging.getLogger(__name__)


CIO_DEFAULT_REPOS = [
    'http://repo.continuum.io/pkgs'
]

INFO_STRING = '''
               target : %s
             platform : %s
conda command version : %s
       root directory : %s
   packages directory : %s
      repository URLS : %s
environment locations : %s
'''

VERSION = __version__

ROOT_DIR = sys.prefix

ROOT = ROOT_DIR # This is deprecated, do not use in new code

PACKAGES_DIR = join(ROOT_DIR, 'pkgs')


DEFAULT_PYTHON_SPEC='python=2.7'
DEFAULT_NUMPY_SPEC='numpy=1.7'

def _load_condarc(path):
    try:
        import yaml
    except ImportError:
        log.warn("yaml module missing, cannot read .condarc files")
        return None
    try:
        rc = yaml.load(open(path))
    except IOError:
        return None
    log.debug("loaded: %s" % path)
    return rc


class config(object):

    __slots__ = ['_rc']

    def __init__(self):
        self._rc = None

        # try to load .condarc file from users home directory
        home = getenv('USERPROFILE') or getenv('HOME')
        self._rc = _load_condarc(join(home, '.condarc'))

        if not self._rc:
            self._rc = _load_condarc(join(ROOT_DIR, '.condarc'))

    @property
    def conda_version(self):
        return VERSION

    @property
    def target(self):
        env_target = getenv('CIO_TARGET')
        if env_target:
            return env_target

        if 'AnacondaPro' in sys.version:
            return 'pro'
        elif 'AnacondaCE' in sys.version:
            return 'ce'
        else:
            return 'unknown'

    @property
    def platform(self):
        sys_map = {'linux2': 'linux', 'darwin': 'osx', 'win32': 'win'}
        bits = int(platform.architecture()[0][:2])
        system = sys_map.get(sys.platform, 'unknown')
        return '%s-%d' % (system, bits)

    @property
    def root_dir(self):
        return ROOT_DIR

    @property
    def packages_dir(self):
        return PACKAGES_DIR

    @property
    def system_location(self):
        return join(ROOT_DIR, 'envs')

    @property
    def user_locations(self):
        locations = []
        if self._rc:
            locations.extend(self._rc.get('locations', []))
        return sorted(abspath(expanduser(location)) for location in locations)

    @property
    def locations(self):
        return sorted(self.user_locations + [self.system_location])

    @property
    def default_environment(self):
        return environment(self, ROOT_DIR)

    @property
    def environments(self):
        envs = []
        for location in self.locations:
            if not exists(location):
                log.warning("location '%s' does not exist" % location)
                continue
            for fn in listdir(location):
                prefix = join(location, fn)
                if isdir(prefix):
                    try:
                        envs.append(environment(self, prefix))
                    except RuntimeError as e:
                        log.info('%s' % e)
        envs.append(self.default_environment)
        return sorted(envs)

    @property
    def repo_base_urls(self):
        if getenv('CIO_TEST'):
            return ['http://filer/test-pkgs', 'http://filer/pkgs']
        elif self._rc:
            return self._rc['repositories']
        else:
            return CIO_DEFAULT_REPOS

    @property
    def repo_package_urls(self):
        return [
            '%s/%s/' % (url, self.platform) for url in self.repo_base_urls
        ]

    @property
    def available_packages(self):
        res = set()
        canonical_names = available(self.packages_dir)
        for name in canonical_names:
            try:
                res.add(self.index.lookup_from_canonical_name(name))
            except KeyError:
                log.debug("unknown available package '%s'" % name)
        return res

    def lookup_environment(self, prefix):
        envs = dict((env.prefix, env) for env in self.environments)
        try:
            return envs[prefix]
        except:
            log.debug('creating environment for prefix: %s' % prefix)
            return environment(self, prefix)

    def __str__(self):
        return INFO_STRING % (
            self.target,
            self.platform,
            self.conda_version,
            self.root_dir,
            self.packages_dir,
            self.repo_package_urls,
            self.locations,
        )

    def __repr__(self):
        return 'config()'
