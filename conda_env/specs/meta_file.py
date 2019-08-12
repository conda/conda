# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os

from .. import env


class MetaFileSpec(object):
    _environment = None
    extensions = set(('.yaml', ))

    def __init__(self, filename=None, install_test=False, **kwargs):
        self.filename = filename
        self.install_test = install_test
        self.msg = None

    def can_handle(self):
        if os.path.basename(self.filename) != "meta.yaml":
            return False

        try:
            from conda_build.metadata import MetaData
        except ImportError:
            self.msg = "conda_build package not installed"
            return False

        try:
            metadata = MetaData(self.filename)
        except Exception:
            self.msg = "{} is not a valid meta.yaml file".format(self.filename)
            return False
        self._environment = env.from_meta(metadata, install_test=self.install_test)
        return True

    @property
    def environment(self):
        if not self._environment:
            self.can_handle()
        return self._environment
