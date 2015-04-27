import re
from conda.resolve import normalized_version
from ..exceptions import EnvironmentFileDoesNotExist, EnvironmentFileNotDownloaded, CondaEnvException
try:
    from binstar_client import errors
    from binstar_client.utils import get_binstar
except ImportError:
    raise CondaEnvException("Binstar not installed")


ENVIRONMENT_TYPE = 'env'


def get_instance(handle):
    return BinstarLoader(handle)


class BinstarLoader(object):
    def __init__(self, handle):
        self.handle = handle
        self.binstar = get_binstar()
        self.package = None
        self.quiet = False
        self._username = None
        self._packagename = None

    def can_download(self):
        """
        Validates loader can download environment definition.
        :return: True or False
        """
        # TODO: log information about trying to find the package in binstar.org
        return self.valid_handle() and self.package_exists()

    def get(self):
        """
        Validates loader can download environment definition
        :return: yaml string
        :exceptions: EnvironmentFileDoesNotExist, EnvironmentFileNotDownloaded
        """
        file_data = [data for data in self.package['files'] if data['type'] == ENVIRONMENT_TYPE]
        if not len(file_data):
            raise EnvironmentFileDoesNotExist(self.handle)

        versions = {normalized_version(d['version']): d['version'] for d in file_data}
        latest_version = versions[max(versions)]
        file_data = [data for data in self.package['files'] if data['version'] == latest_version]
        req = self.binstar.download(self.username, self.packagename, latest_version, file_data[0]['basename'])
        if req is None:
            raise EnvironmentFileNotDownloaded(self.username, self.packagename)

        self.info("Successfully fetched {} from Binstar.org".format(self.handle))
        return req.raw.read()

    def valid_handle(self):
        return re.match("^(.+)/(.+)$", self.handle)

    def package_exists(self):
        """
        Checks whether a package exists on binstar or not.
        :return: True or False
        """
        try:
            self.package = self.binstar.package(self.username, self.packagename)
        except errors.NotFound:
            self.info("{} was not found on Binstar.org.\n"
                      "You may need to be logged in. Try running:\n"
                      "    binstar login"
                      "".format(self.handle))

        return self.package is not None

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
