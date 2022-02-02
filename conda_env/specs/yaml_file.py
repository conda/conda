# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from .. import env
from ..exceptions import EnvironmentFileNotFound


class YamlFileSpec:
    _environment = None
    extensions = {".yaml", ".yml"}

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
        except TypeError:
            self.msg = f"{self.filename} is not a valid yaml file."
            return False

    @property
    def environment(self):
        if not self._environment:
            self.can_handle()
        return self._environment
