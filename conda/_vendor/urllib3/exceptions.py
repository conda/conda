# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


class HTTPError(Exception):
    "Base exception used by this module."
    pass


class LocationValueError(ValueError, HTTPError):
    "Raised when there is something wrong with a given URL input."
    pass


class LocationParseError(LocationValueError):
    "Raised when get_host or similar fails to parse the URL input."

    def __init__(self, location):
        message = "Failed to parse: %s" % location
        HTTPError.__init__(self, message)

        self.location = location
