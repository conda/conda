class ProgressiveException(Exception):
    """Base class for exceptions raised by ``progressive``"""


class ColorUnsupportedError(ProgressiveException):
    """Color is not supported by terminal"""


class WidthOverflowError(ProgressiveException):
    """Terminal is not wide enough for the bar attempting to be written"""


class LengthOverflowError(ProgressiveException):
    """Terminal is not long enough to display hierarchy"""
