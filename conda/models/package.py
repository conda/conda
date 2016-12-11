# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger

from .channel import Channel
from .dist import Dist
from ..version import normalized_version

log = getLogger(__name__)
stderrlog = getLogger('stderrlog')


class Package(object):
    """
    The only purpose of this class is to provide package objects which
    are sortable.

    ^^^ someday it should probably have more than just this purpose
        or get rid of it altogether and use one of the other model objects to sort

    Not a new-type model.  Total legacy class.
    """
    def __init__(self, fn, info):
        if isinstance(fn, Dist):
            self.fn = fn.to_filename()
            self.dist = fn
        else:
            self.fn = fn
            self.dist = Dist(fn)
        self.name = info.get('name')
        self.version = info.get('version')
        self.build = info.get('build')
        self.build_number = info.get('build_number')
        self.channel = info.get('channel')
        self.schannel = info.get('schannel')
        self.priority = info.get('priority', None)
        if self.schannel is None:
            self.schannel = Channel(self.channel).canonical_name
        try:
            self.norm_version = normalized_version(self.version)
        except ValueError:
            stderrlog.error("\nThe following stack trace is in reference to "
                            "package:\n\n\t%s\n\n" % fn)
            raise
        self.info = info

    def _asdict(self):
        result = self.info.dump()
        result['fn'] = self.fn
        result['norm_version'] = str(self.norm_version)
        return result

    def __lt__(self, other):
        if self.name != other.name:
            raise TypeError('cannot compare packages with different '
                            'names: %r %r' % (self.fn, other.fn))
        return ((self.norm_version, self.build_number, self.build) <
                (other.norm_version, other.build_number, other.build))

    def __eq__(self, other):
        if not isinstance(other, Package):
            return False
        if self.name != other.name:
            return False
        return ((self.norm_version, self.build_number, self.build) ==
                (other.norm_version, other.build_number, other.build))

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        return other < self

    def __le__(self, other):
        return not (other < self)

    def __ge__(self, other):
        return not (self < other)
