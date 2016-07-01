# -*- coding: utf-8 -*-
#
# progressbar  - Text progress bar library for Python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''Default ProgressBar widgets'''

from __future__ import print_function, division, absolute_import

import datetime
import math


try:
    from abc import ABCMeta, abstractmethod
    abstractmethod; # silence pyflakes
except ImportError:
    AbstractWidget = object
    abstractmethod = lambda fn: fn
else:
    AbstractWidget = ABCMeta('AbstractWidget', (object,), {})


def format_updatable(updatable, pbar):
    if hasattr(updatable, 'update'): return updatable.update(pbar)
    else: return updatable


class Widget(AbstractWidget):
    '''The base class for all widgets

    The ProgressBar will call the widget's update value when the widget should
    be updated. The widget's size may change between calls, but the widget may
    display incorrectly if the size changes drastically and repeatedly.

    The boolean TIME_SENSITIVE informs the ProgressBar that it should be
    updated more often because it is time sensitive.
    '''

    TIME_SENSITIVE = False
    __slots__ = ()

    @abstractmethod
    def update(self, pbar):
        '''Updates the widget.

        pbar - a reference to the calling ProgressBar
        '''


class Timer(Widget):
    'Widget which displays the elapsed seconds.'

    __slots__ = ('format',)
    TIME_SENSITIVE = True

    def __init__(self, format='Elapsed Time: %s'):
        self.format = format

    @staticmethod
    def format_time(seconds):
        'Formats time as the string "MM:SS".'
        seconds = math.ceil(seconds)
        m, s = divmod(seconds, 60)
        return "%d:%02d" % (m, s)

    def update(self, pbar):
        'Updates the widget to show the elapsed time.'

        return self.format % self.format_time(pbar.seconds_elapsed)


class ETA(Timer):
    'Widget which attempts to estimate the time of arrival.'

    TIME_SENSITIVE = True

    def update(self, pbar):
        'Updates the widget to show the ETA or total time when finished.'

        if pbar.currval == 0:
            return '--:-- '
        elif pbar.finished == 1:
            return '%s ' % self.format_time(0)
        else:
            elapsed = pbar.seconds_elapsed
            eta = math.ceil(elapsed * pbar.max_value / pbar.currval - elapsed)
            return '%s ' % self.format_time(eta)


class FileTransferSpeed(Widget):
    'Widget for showing the transfer speed (useful for file transfers).'

    prefixes = ' kMGTPEZY'
    __slots__ = ('unit', 'format')

    def __init__(self, unit='B'):
        self.unit = unit
        self.format = ' %6.2f %s%s/s'

    def update(self, pbar):
        'Updates the widget with the current SI prefixed speed.'

        if pbar.seconds_elapsed < 2e-6 or pbar.currval < 2e-6: # =~ 0
            scaled = power = 0
        else:
            speed = pbar.currval / pbar.seconds_elapsed
            power = int(math.log(speed, 1000))
            scaled = speed / 1000.**power

        return self.format % (scaled, self.prefixes[power], self.unit)


class Counter(Widget):
    'Displays the current count'

    __slots__ = ('format',)

    def __init__(self, format='%d'):
        self.format = format

    def update(self, pbar):
        return self.format % pbar.currval