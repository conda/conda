import os
import time
from collections import namedtuple
from .. import exceptions
try:
    from binstar_client.utils import get_binstar
    from binstar_client import errors
except ImportError:
    get_binstar = None


ENVIRONMENT_TYPE = 'env'

# TODO: refactor binstar so that individual arguments are passed in instead of an arg object
binstar_args = namedtuple('binstar_args', ['site', 'token'])


def is_installed():
    """
    is Binstar-cli installed?
    :return: True/False
    """
    return get_binstar is not None


class Uploader(object):
    """
    Upload environments to Binstar
    * Check if user is logged (offer to log in if it's not)
    * Check if package exist (create if not)
    * Check if distribution exist (overwrite if force=True)
    * Upload environment.yml
    """

    _user = None
    _username = None
    _binstar = None

    def __init__(self, packagename, env_file, **kwargs):
        self.packagename = packagename
        self.file = env_file
        self.summary = kwargs.get('summary')
        self.env_data = kwargs.get('env_data')
        self.basename = os.path.basename(env_file)

    @property
    def version(self):
        return time.strftime('%Y.%m.%d.%H%M')

    @property
    def user(self):
        if self._user is None:
            self._user = self.binstar.user()
        return self._user

    @property
    def binstar(self):
        if self._binstar is None:
            self._binstar = get_binstar()
        return self._binstar

    @property
    def username(self):
        if self._username is None:
            self._username = self.user['login']
        return self._username

    def authorized(self):
        try:
            return self.user is not None
        except errors.Unauthorized:
            return False

    def upload(self):
        """
        Prepares and uploads env file
        :return: True/False
        """
        print("Uploading environment %s to anaconda-server (%s)... " %
              (self.packagename, self.binstar.domain))
        if self.is_ready():
            with open(self.file, mode='rb') as envfile:
                return self.binstar.upload(self.username, self.packagename,
                                           self.version, self.basename, envfile,
                                           distribution_type=ENVIRONMENT_TYPE, attrs=self.env_data)
        else:
            raise exceptions.AlreadyExist()

    def is_ready(self):
        """
        Ensures package namespace and distribution
        :return: True or False
        """
        return self.ensure_package_namespace() and self.ensure_distribution()

    def ensure_package_namespace(self):
        """
        Ensure that a package namespace exists. This is required to upload a file.
        """
        try:
            self.binstar.package(self.username, self.packagename)
        except errors.NotFound:
            self.binstar.add_package(self.username, self.packagename, self.summary)

        # TODO: this should be removed as a hard requirement of binstar
        try:
            self.binstar.release(self.username, self.packagename, self.version)
        except errors.NotFound:
            self.binstar.add_release(self.username, self.packagename, self.version, {}, '', '')

        return True

    def ensure_distribution(self):
        """
        Ensure that a package distribution does not exist.
        """
        try:
            self.binstar.distribution(self.username, self.packagename, self.version, self.basename)
        except errors.NotFound:
            return True
        else:
            return False
