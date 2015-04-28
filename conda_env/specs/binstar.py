import re
from conda.resolve import normalized_version
from ..exceptions import EnvironmentFileDoesNotExist, EnvironmentFileNotDownloaded, CondaEnvException
try:
    from binstar_client import errors
    from binstar_client.utils import get_binstar
except ImportError:
    raise CondaEnvException("Binstar not installed")

ENVIRONMENT_TYPE = 'env'


class BinstarSpec(object):
    """
    spec = BinstarSpec('darth/deathstar')
    spec.can_process() # => True / False
    spec.environment # => YAML string
    :raises: EnvironmentFileDoesNotExist, EnvironmentFileNotDownloaded
    """

    _environment = None
    _username = None
    _packagename = None
    _package = None

    def __init__(self, handle):
        self.handle = handle
        self.binstar = get_binstar()
        self.quiet = False
        self.info("Successfully fetched {} from Binstar.org".format(self.handle))

    def can_process(self):
        """
        Validates loader can process environment definition.
        :return: True or False
        """
        # TODO: log information about trying to find the package in binstar.org
        return self.valid_handle() and self.package

    def valid_handle(self):
        return re.match("^(.+)/(.+)$", self.handle)

    @property
    def environment(self):
        """
        :raises: EnvironmentFileDoesNotExist, EnvironmentFileNotDownloaded
        """
        if self._environment is None:
            file_data = [data for data in self.package['files'] if data['type'] == ENVIRONMENT_TYPE]
            if not len(file_data):
                raise EnvironmentFileDoesNotExist(self.handle)

            versions = {normalized_version(d['version']): d['version'] for d in file_data}
            latest_version = versions[max(versions)]
            file_data = [data for data in self.package['files'] if data['version'] == latest_version]
            req = self.binstar.download(self.username, self.packagename, latest_version, file_data[0]['basename'])
            if req is None:
                raise EnvironmentFileNotDownloaded(self.username, self.packagename)
            self._environment = req.raw.read()
        return self._environment

    @property
    def package(self):
        if self._package is None:
            try:
                self._package = self.binstar.package(self.username, self.packagename)
            except errors.NotFound:
                self.info("{} was not found on Binstar.org.\n"
                          "You may need to be logged in. Try running:\n"
                          "    binstar login"
                          "".format(self.handle))
        return self._package

    @property
    def username(self):
        if self._username is None:
            self._username = self.parse()[0]
        return self._username

    @property
    def packagename(self):
        if self._packagename is None:
            self._packagename = self.parse()[1]
        return self._packagename

    def parse(self):
        """Parse environment definition handle"""
        return self.handle.split('/', 1)

    def info(self, msg):
        if not self.quiet:
            print(msg)
