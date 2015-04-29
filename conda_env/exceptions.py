class CondaEnvException(Exception):
    pass


class CondaEnvRuntimeError(RuntimeError, CondaEnvException):
    pass


class EnvironmentFileNotFound(CondaEnvException):
    def __init__(self, filename, *args, **kwargs):
        msg = '{} file not found'.format(filename)
        self.filename = filename
        super(EnvironmentFileNotFound, self).__init__(msg, *args, **kwargs)


class NoBinstar(CondaEnvRuntimeError):
    def __init__(self):
        msg = 'The binstar client must be installed to perform this action'
        super(NoBinstar, self).__init__(msg)


class AlreadyExist(CondaEnvException):
    def __init__(self):
        msg = 'The environment path already exists'
        super(AlreadyExist, self).__init__(msg)
