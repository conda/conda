# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda import CondaError


class CondaEnvException(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = "%s" % message
        super().__init__(msg, *args, **kwargs)


class EnvironmentFileNotFound(CondaEnvException):
    def __init__(self, filename, *args, **kwargs):
        msg = f"'{filename}' file not found"
        self.filename = filename
        super().__init__(msg, *args, **kwargs)


class EnvironmentFileExtensionNotValid(CondaEnvException):
    def __init__(self, filename, *args, **kwargs):
        msg = f"'{filename}' file extension must be one of '.txt', '.yaml' or '.yml'"
        self.filename = filename
        super().__init__(msg, *args, **kwargs)


class NoBinstar(CondaError):
    def __init__(self):
        msg = 'The anaconda-client cli must be installed to perform this action'
        super().__init__(msg)


class AlreadyExist(CondaError):
    def __init__(self):
        msg = 'The environment path already exists'
        super().__init__(msg)


class EnvironmentAlreadyInNotebook(CondaError):
    def __init__(self, notebook, *args, **kwargs):
        msg = "The notebook {} already has an environment"
        super().__init__(msg, *args, **kwargs)


class EnvironmentFileDoesNotExist(CondaError):
    def __init__(self, handle, *args, **kwargs):
        self.handle = handle
        msg = f"{handle} does not have an environment definition"
        super().__init__(msg, *args, **kwargs)


class EnvironmentFileNotDownloaded(CondaError):
    def __init__(self, username, packagename, *args, **kwargs):
        msg = f"{username}/{packagename} file not downloaded"
        self.username = username
        self.packagename = packagename
        super().__init__(msg, *args, **kwargs)


class SpecNotFound(CondaError):
    def __init__(self, msg, *args, **kwargs):
        super().__init__(msg, *args, **kwargs)


class InvalidLoader(Exception):
    def __init__(self, name):
        msg = f"Unable to load installer for {name}"
        super().__init__(msg)


class NBFormatNotInstalled(CondaError):
    def __init__(self):
        msg = """nbformat is not installed. Install it with:
        conda install nbformat
        """
        super().__init__(msg)
