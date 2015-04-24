from conda.resolve import normalized_version
from binstar_client.utils import get_binstar
from binstar_client import errors
from conda_env.exceptions import EnvironmentFileNotDownloaded, EnvironmentUsernameRequired, PackageNotFound

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
        self.username, self.packagename, self.version_required = self.parse(package_handle)

    @staticmethod
    def parse(package_handle):
        """
        Parse package_handle in the form:
        >>> package_handle = 'malev/conda-env==2.1'
        ('malev', 'conda-env', '2.1')
        :param package_handle:
        :return: (username, package_name, version_requires)
        """

        if '/' in package_handle:
            username, package_version = package_handle.split('/', 1)
        else:
            raise EnvironmentUsernameRequired()

        if '==' in package_version:
            packagename, version = package_version.split('==', 1)
        else:
            version = None
            packagename = package_version

        return username, packagename, version

    def download(self):
        if self.version_required:
            req = self._download(self.version_required)
        else:
            req = self._download(self.latest_version)

        if req is None:
            raise EnvironmentFileNotDownloaded(self.username, self.packagename)
        else:
            with open(self.filename, 'w') as fd:
                fd.write(req.raw.read())

    def _download(self, version):
        return self.binstar.download(self.username, self.packagename,
                                     version, self.file_data[0]['basename'])

    @property
    def latest_version(self):
        versions = {normalized_version(d['version']): d['version'] for d in self.file_data}
        return versions[max(versions)]

    @property
    def package(self):
        if self._package is None:
            try:
                self._package = self.binstar.package(self.username, self.packagename)
            except errors.NotFound:
                raise PackageNotFound(self.username, self.packagename)
        return self._package

    @property
    def file_data(self):
        return [data for data in self.package['files'] if data['type'] == ENVIRONMENT_TYPE]
