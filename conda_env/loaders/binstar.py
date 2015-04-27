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
        username, packagename = self.parse()
        file_data = [data for data in self.package['files'] if data['type'] == ENVIRONMENT_TYPE]
        if not len(file_data):
            raise EnvironmentFileDoesNotExist(self.handle)

        versions = {normalized_version(d['version']): d['version'] for d in file_data}
        latest_version = versions[max(versions)]
        file_data = [data for data in self.package['files'] if data['version'] == latest_version]
        req = self.binstar.download(username, packagename, latest_version, file_data[0]['basename'])
        if req is None:
            raise EnvironmentFileNotDownloaded(username, packagename)

        return req.raw.read()

    def valid_handle(self):
        return re.match("^(.+)/(.+)$", self.handle)

    def package_exists(self):
        """
        Checks whether a package exists on binstar or not.
        :return: True or False
        """
        username, packagename = self.parse()
        try:
            self.package = self.binstar.package(username, packagename)
        except errors.NotFound:
            pass

        return self.package is not None

    def parse(self):
        """Parse environment definition handle"""
        return self.handle.split('/', 1)
