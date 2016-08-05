# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import WARN, getLogger, ERROR

from ..common.io import attach_stderr_handler

log = getLogger(__name__)


def initialize_logging():
    initialize_root_logger()
    initialize_conda_logger()

def initialize_root_logger(level=ERROR):
    attach_stderr_handler(level)

def initialize_conda_logger(level=WARN):
    attach_stderr_handler(level, 'conda')
