# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.exceptions import EnvironmentFileEmpty, EnvironmentFileNotFound

from .. import env


class YamlFileSpec(object):
    _environment = None
    extensions = set(('.yaml', '.yml'))

    def __init__(self, filename=None, **kwargs):
        self.filename = filename
        self.msg = None

    def can_handle(self):
        try:
            self._environment = env.from_file(self.filename)
            return True
        except EnvironmentFileNotFound as e:
            self.msg = str(e)
            return False
        except EnvironmentFileEmpty as e:
            self.msg = e.message
            return False
        except TypeError:
            self.msg = "{} is not a valid yaml file.".format(self.filename)
            return False

    @property
    def environment(self):
        if not self._environment:
            self.can_handle()
        return self._environment
