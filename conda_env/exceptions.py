# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda import CondaError


class CondaEnvException(CondaError):
    def __init__(self, message, *args, **kwargs):
        msg = "%s" % message
        super(CondaEnvException, self).__init__(msg, *args, **kwargs)


class EnvironmentFileNotFound(CondaEnvException):
    def __init__(self, filename, *args, **kwargs):
        msg = "'{}' file not found".format(filename)
        self.filename = filename
        super(EnvironmentFileNotFound, self).__init__(msg, *args, **kwargs)


class EnvironmentFileExtensionNotValid(CondaEnvException):
    def __init__(self, filename, *args, **kwargs):
        msg = "'{}' file extension must be one of '.txt', '.yaml' or '.yml'".format(filename)
        self.filename = filename
        super(EnvironmentFileExtensionNotValid, self).__init__(msg, *args, **kwargs)


class EnvironmentFileNotDownloaded(CondaError):
    def __init__(self, username, packagename, *args, **kwargs):
        msg = '{}/{} file not downloaded'.format(username, packagename)
        self.username = username
        self.packagename = packagename
        super(EnvironmentFileNotDownloaded, self).__init__(msg, *args, **kwargs)


class SpecNotFound(CondaError):
    def __init__(self, msg, *args, **kwargs):
        super(SpecNotFound, self).__init__(msg, *args, **kwargs)
