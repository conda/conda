class CondaEnvException(Exception):
    pass


class CondaEnvRuntimeError(RuntimeError, CondaEnvException):
    pass


class EnvironmentFileNotFound(CondaEnvException):
    def __init__(self, filename, *args, **kwargs):
        msg = '{} file not found'.format(filename)
        self.filename = filename
        super(EnvironmentFileNotFound, self).__init__(msg, *args, **kwargs)


class EnvironmentFileDoesNotExist(CondaEnvRuntimeError):
    def __init__(self, handle, *args, **kwargs):
        self.handle = handle
        msg = "{} does not have an environment definition".format(handle)
        super(EnvironmentFileDoesNotExist, self).__init__(msg, *args, **kwargs)


class EnvironmentFileNotDownloaded(CondaEnvRuntimeError):
    def __init__(self, username, packagename, *args, **kwargs):
        msg = '{}/{} file not downloaded'.format(username, packagename)
        self.username = username
        self.packagename = packagename
        super(EnvironmentFileNotDownloaded, self).__init__(msg, *args, **kwargs)


class LoaderNotFound(CondaEnvRuntimeError):
    def __init__(self, handle, *args, **kwargs):
        msg = '{} coudn\'t be processed'.format(handle)
        super(LoaderNotFound, self).__init__(msg, *args, **kwargs)
