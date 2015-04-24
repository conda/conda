from conda.resolve import normalized_version
from binstar_client.utils import get_binstar
from binstar_client import errors
from conda_env.exceptions import EnvironmentFileNotDownloaded

ENVIRONMENT_TYPE = 'env'


def is_installed():
    """
    is Binstar-cli installed?
    :return: True/False
    """
    return get_binstar is not None


class Downloader(object):
    """
    Download environmnets from binstar
    """
    def __init__(self, package_handle, filename):
        self.binstar = get_binstar()
        self.filename = filename
        self._package = None
        self.username, self.package_name, self.version_required = self.parse(package_handle)

    @staticmethod
    def parse(package_handle):
        """
        Parse package_handle in the form:
        >>> package_handle = 'malev/conda-env==2.1'
        ('malev', 'conda-env', '2.1')
        :param package_handle:
        :return: (username, package_name, version_requires)
        """
        username = None
        version_required = None
        if '/' in package_handle:
            username, spec_str = package_handle.split('/', 1)

        if '==' in package_handle:
            package_name, version_required = package_handle.split('==', 1)
        else:
            package_name = package_handle

        return username, package_name, version_required

    def valid_handle(self):
        return self.username and self.package_name

    def package_present(self):
        try:
            self.package
        except errors.NotFound:
            return False
        return True

    def valid_package(self):
        return len(self.file_data) > 0

    def download(self):
        if self.version_required:
            req = self._download(self.version_required)
        else:
            req = self._download(self.latest_version)

        if req is None:
            raise EnvironmentFileNotDownloaded(self.filename)
        else:
            with open(self.filename, 'w') as fd:
                fd.write(req.raw.read())

    def _download(self, version):
        return self.binstar.download(self.username, self.package_name,
                                     version, self.file_data[0]['basename'])

    @property
    def latest_version(self):
        versions = {normalized_version(d['version']): d['version'] for d in self.file_data}
        return versions[max(versions)]

    @property
    def package(self):
        if self._package is None:
            self._package = self.binstar.package(self.username, self.package_name)
        return self._package

    @property
    def file_data(self):
        return [data for data in self.package['files'] if data['type'] == ENVIRONMENT_TYPE]
