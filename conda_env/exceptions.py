class CondaEnvException(Exception):
    pass


class EnvironmentFileNotFound(CondaEnvException):
    def __init__(self, filename, *args, **kwargs):
        msg = '{} file not found'.format(filename)
        self.filename = filename
        super(EnvironmentFileNotFound, self).__init__(msg, *args, **kwargs)


class EnvironmentFileNotDownloaded(CondaEnvException):
    def __init__(self, filename, *args, **kwargs):
        msg = '{} file not downloaded'.format(filename)
        self.filename = filename
        super(EnvironmentFileNotDownloaded, self).__init__(msg, *args, **kwargs)
