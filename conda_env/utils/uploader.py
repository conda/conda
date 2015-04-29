import os
from collections import namedtuple
from .. import exceptions
try:
    from binstar_client.utils import get_binstar
except ImportError:
    get_binstar = None
from binstar_client import errors
from binstar_client.commands.login import interactive_login


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

    user = None

    def __init__(self, packagename, env_file, summary=None, env_data={}):
        self.packagename = packagename
        self.file = env_file
        self.summary = summary
        self.env_data = env_data

        self.binstar = get_binstar()
        self.user = self.ensure_loggedin()
        self.basename = os.path.basename(env_file)
        self.username = self.user['login']
        self.version = '1.0'

    def upload(self, force=False):
        """
        Prepares and uploads env file
        :return: True/False
        """
        print("Uploading environment %s to anaconda-server (%s)... " % (self.packagename, self.binstar.domain))
        if force or self.is_ready(force):
            return self.binstar.upload(self.username, self.packagename,
                                       self.version, self.basename, open(self.file),
                                       distribution_type=ENVIRONMENT_TYPE, attrs=self.env_data)
        else:
            raise exceptions.AlreadyExist()

    def ensure_loggedin(self):
        try:
            return self.binstar.user()
        except errors.Unauthorized:
            print('The action you are performing requires authentication, '
                  'please sign in to binstar:')
            interactive_login(binstar_args(None, None))
            # TODO: refactor binstar to make this easier e.g `binstar.reload_token() or binstar.ensure_login()`
            # In binstar cli the binstar object is re-created.
            self.binstar.token = get_binstar().token
            self.binstar._session.headers.update({'Authorization': 'token %s' % self.binstar.token})
            return self.binstar.user()

    def is_ready(self, force):
        """
        Ensures package namespace and distribution
        :return: True or False
        """
        return self.ensure_package_namespace() and self.ensure_distribution(force)

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

    def ensure_distribution(self, force=False):
        """
        Ensure that a package namespace exists. This is required to upload a file.
        """
        try:
            self.binstar.distribution(self.username, self.packagename, self.version, self.basename)
        except errors.NotFound:
            return True
        else:
            if force:
                self.binstar.remove_dist(self.username, self.packagename, self.version, self.basename)
                return True
            return False
