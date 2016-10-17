import re
from conda.resolve import normalized_version
from .. import env
from ..exceptions import EnvironmentFileNotDownloaded
try:
    from binstar_client import errors
    from binstar_client.utils import get_binstar
except ImportError:
    get_binstar = None

ENVIRONMENT_TYPE = 'env'
# TODO: isolate binstar related code into conda_env.utils.binstar


class BinstarSpec(object):
    """
    spec = BinstarSpec('darth/deathstar')
    spec.can_handle() # => True / False
    spec.environment # => YAML string
    spec.msg # => Error messages
    :raises: EnvironmentFileDoesNotExist, EnvironmentFileNotDownloaded
    """

    _environment = None
    _username = None
    _packagename = None
    _package = None
    _file_data = None
    msg = None

    def __init__(self, name=None, **kwargs):
        self.name = name
        self.quiet = False
        if get_binstar is not None:
            self.binstar = get_binstar()
        else:
            self.binstar = None

    def can_handle(self):
        """
        Validates loader can process environment definition.
        :return: True or False
        """
        # TODO: log information about trying to find the package in binstar.org
        if self.valid_name():
            if self.binstar is None:
                self.msg = "Please install binstar"
                return False
            return self.package is not None and self.valid_package()
        return False

    def valid_name(self):
        """
        Validates name
        :return: True or False
        """
        if re.match("^(.+)/(.+)$", str(self.name)) is not None:
            return True
        elif self.name is None:
            self.msg = "Can't process without a name"
        else:
            self.msg = "Invalid name, try the format: user/package"
        return False

    def valid_package(self):
        """
        Returns True if package has an environment file
        :return: True or False
        """
        return len(self.file_data) > 0

    @property
    def file_data(self):
        if self._file_data is None:
            self._file_data = [data
                               for data in self.package['files']
                               if data['type'] == ENVIRONMENT_TYPE]
        return self._file_data

    @property
    def environment(self):
        """
        :raises: EnvironmentFileNotDownloaded
        """
        if self._environment is None:
            versions = [{'normalized': normalized_version(d['version']), 'original': d['version']}
                        for d in self.file_data]
            latest_version = max(versions, key=lambda x: x['normalized'])['original']
            file_data = [data
                         for data in self.package['files']
                         if data['version'] == latest_version]
            req = self.binstar.download(self.username, self.packagename, latest_version,
                                        file_data[0]['basename'])
            if req is None:
                raise EnvironmentFileNotDownloaded(self.username, self.packagename)
            self._environment = req.text
        return env.from_yaml(self._environment)

    @property
    def package(self):
        if self._package is None:
            try:
                self._package = self.binstar.package(self.username, self.packagename)
            except errors.NotFound:
                self.msg = "{} was not found on anaconda.org.\n"\
                           "You may need to be logged in. Try running:\n"\
                           "    anaconda login".format(self.name)
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
        return self.name.split('/', 1)
