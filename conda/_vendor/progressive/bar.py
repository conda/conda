# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import unicode_literals

from .cursor import Cursor
from .util import floor, ensure, u
from .exceptions import ColorUnsupportedError, WidthOverflowError
from .widgets import WidgetHFill, format_updatable
from time import time
class Bar(object):
    """Progress Bar with blessings

    Several parts of this class are thanks to Erik Rose's implementation
    of ``ProgressBar`` in ``nose-progressive``, licensed under
    The MIT License.
    `MIT <http://opensource.org/licenses/MIT>`_
    `nose-progressive/noseprogressive/bar.py <https://github.com/erikrose/nose-progressive/blob/master/noseprogressive/bar.py>`_

    Terminal with 256 colors is recommended. See
        `this <http://pastelinux.wordpress.com/2010/12/01/upgrading-linux-terminal-to-256-colors/>`_ for Ubuntu
        installation as an example.

    :type  term: blessings.Terminal|NoneType
    :param term: blessings.Terminal instance for the terminal of display
    :type  max_value: int
    :param max_value: The capacity of the bar, i.e., ``value/max_value``
    :type  width: str
    :param width: Must be of format {num: int}{unit: c|%}. Unit "c"
        can be used to specify number of maximum columns; unit "%".
        to specify percentage of the total terminal width to use.
        e.g., "20c", "25%", etc.
    :type  title_pos: str
    :param title_pos: Position of title relative to the progress bar;
        can be any one of ["left", "right", "above", "below"]
    :type  title: str
    :param title: Title of the progress bar
    :type  num_rep: str
    :param num_rep: Numeric representation of completion;
        can be one of ["fraction", "percentage"]
    :type  indent: int
    :param indent: Spaces to indent the bar from the left-hand side
    :type  filled_color: str|int
    :param filled_color: color of the ``filled_char``; can be a string
        of the color's name or number representing the color; see the
        ``blessings`` documentation for details
    :type  empty_color: str|int
    :param empty_color: color of the ``empty_char``
    :type  back_color: str|NoneType
    :param back_color: Background color of the progress bar; must be
        a string of the color name, unused if numbers used for
        ``filled_color`` and ``empty_color``. If set to None,
        will not be used.
    :type  filled_char: unicode
    :param filled_char: Character representing completeness on the
        progress bar
    :type  empty_char: unicode
    :param empty_char: The complement to ``filled_char``
    :type  start_char: unicode
    :param start_char: Character at the start of the progress bar
    :type  end_char: unicode
    :param end_char: Character at the end of the progress bar
    :type  fallback: bool
    :param fallback: If this is set, if the terminal does not support
        provided colors, this will fall back to plain formatting
        that works on terminals with no color support, using the
        provided ``fallback_empty_char` and ``fallback_filled_char``
    :type  force_color: bool|NoneType
    :param force_color: ``True`` forces color to be used even if it
        may not be supported by the terminal; ``False`` forces use of
        the fallback formatting; ``None`` does not force anything
        and allows automatic detection as usual.
    :type widgets : class
    :param widgets: the widgets, such as timer, file transfer speed
    """

    def __init__(
            self, term=None, max_value=100, width="25%", title_pos="left",
            title="Progress", num_rep="fraction", indent=0, filled_color=2,
            empty_color=7, back_color=None, filled_char=u' ',
            empty_char=u' ', start_char=u'', end_char=u'', fallback=True,
            fallback_empty_char=u'◯', fallback_filled_char=u'◉',
            force_color=None, widgets=None
    ):
        self.cursor = Cursor(term)
        self.term = self.cursor.term

        self._measure_terminal()

        self._width_str = width
        self._max_value = max_value

        ensure(title_pos in ["left", "right", "above", "below"], ValueError,
               "Invalid choice for title position.")
        self._title_pos = title_pos
        self._title = title
        ensure(num_rep in ["fraction", "percentage"], ValueError,
               "num_rep must be either 'fraction' or 'percentage'.")
        self._num_rep = num_rep
        ensure(indent < self.columns, ValueError,
               "Indent must be smaller than terminal width.")
        self._indent = indent

        self._start_char = start_char
        self._end_char = end_char

        # Setup callables and characters depending on if terminal has
        #   has color support
        if force_color is not None:
            supports_colors = force_color
        else:
            supports_colors = self._supports_colors(
                term=self.term,
                raise_err=not fallback,
                colors=(filled_color, empty_color)
            )
        if supports_colors:
            self._filled_char = filled_char
            self._empty_char = empty_char
            self._filled = self._get_format_callable(
                term=self.term,
                color=filled_color,
                back_color=back_color
            )
            self._empty = self._get_format_callable(
                term=self.term,
                color=empty_color,
                back_color=back_color
            )
        else:
            self._empty_char = fallback_empty_char
            self._filled_char = fallback_filled_char
            self._filled = self._empty = lambda s: s

        ensure(self.full_line_width <= self.columns, WidthOverflowError,
               "Attempting to initialize Bar with full_line_width {}; "
               "terminal has width of only {}.".format(
                   self.full_line_width,
                   self.columns))
        self.widgets = widgets
        self.finished = 0
        self.seconds_elapsed = 0
        self.currval = 0
        self.start_time = time()
    ######################
    # Public Attributes #
    ######################

    @property
    def max_width(self):
        """Get maximum width of progress bar

        :rtype: int
        :returns: Maximum column width of progress bar
        """
        value, unit = float(self._width_str[:-1]), self._width_str[-1]

        ensure(unit in ["c", "%"], ValueError,
               "Width unit must be either 'c' or '%'")

        if unit == "c":
            ensure(value <= self.columns, ValueError,
                   "Terminal only has {} columns, cannot draw "
                   "bar of size {}.".format(self.columns, value))
            retval = value
        else:  # unit == "%"
            ensure(0 < value <= 100, ValueError,
                   "value=={} does not satisfy 0 < value <= 100".format(value))
            dec = value / 100
            retval = dec * self.columns

        return floor(retval)

    @property
    def full_line_width(self):
        """Find actual length of bar_str

        e.g., Progress [    |     ] 10/10
        """
        bar_str_len = sum([
            self._indent,
            ((len(self.title) + 1) if self._title_pos in ["left", "right"]
             else 0),  # Title if present
            len(self.start_char),
            self.max_width,  # Progress bar
            len(self.end_char),
            1,  # Space between end_char and amount_complete_str
            len(str(self.max_value)) * 2 + 1  # 100/100
        ])
        return bar_str_len

    @property
    def filled(self):
        """Callable for drawing filled portion of progress bar

        :rtype: callable
        """
        return self._filled

    @property
    def empty(self):
        """Callable for drawing empty portion of progress bar

        :rtype: callable
        """
        return self._empty

    @property
    def max_value(self):
        """The capacity of the bar, i.e., ``value/max_value``"""
        return self._max_value

    @max_value.setter
    def max_value(self, val):
        self._max_value = val

    @property
    def title(self):
        """Title of the progress bar"""
        return self._title

    @title.setter
    def title(self, t):
        self._title = t

    @property
    def start_char(self):
        """Character at the start of the progress bar"""
        return self._start_char

    @start_char.setter
    def start_char(self, c):
        self._start_char = c

    @property
    def end_char(self):
        """Character at the end of the progress bar"""
        return self._end_char

    @end_char.setter
    def end_char(self, c):
        self._end_char = c

    ###################
    # Private Methods #
    ###################

    @staticmethod
    def _supports_colors(term, raise_err, colors):
        """Check if ``term`` supports ``colors``

        :raises ColorUnsupportedError: This is raised if ``raise_err``
            is ``False`` and a color in ``colors`` is unsupported by ``term``
        :type raise_err: bool
        :param raise_err: Set to ``False`` to return a ``bool`` indicating
            color support rather than raising ColorUnsupportedError
        :type  colors: [str, ...]
        """
        for color in colors:
            try:
                if isinstance(color, str):
                    req_colors = 16 if "bright" in color else 8
                    ensure(term.number_of_colors >= req_colors,
                           ColorUnsupportedError,
                           "{} is unsupported by your terminal.".format(color))
                elif isinstance(color, int):
                    ensure(term.number_of_colors >= color,
                           ColorUnsupportedError,
                           "{} is unsupported by your terminal.".format(color))
            except ColorUnsupportedError as e:
                if raise_err:
                    raise e
                else:
                    return False
        else:
            return True

    @staticmethod
    def _get_format_callable(term, color, back_color):
        """Get string-coloring callable

        Get callable for string output using ``color`` on ``back_color``
            on ``term``

        :param term: blessings.Terminal instance
        :param color: Color that callable will color the string it's passed
        :param back_color: Back color for the string
        :returns: callable(s: str) -> str
        """
        if isinstance(color, str):
            ensure(
                any(isinstance(back_color, t) for t in [str, type(None)]),
                TypeError,
                "back_color must be a str or NoneType"
            )
            if back_color:
                return getattr(term, "_".join(
                    [color, "on", back_color]
                ))
            elif back_color is None:
                return getattr(term, color)
        elif isinstance(color, int):
            return term.on_color(color)
        else:
            raise TypeError("Invalid type {} for color".format(
                type(color)
            ))

    def _measure_terminal(self):
        self.lines, self.columns = (
            self.term.height or 24,
            self.term.width or 80
        )

    def _write(self, s, s_length=None, flush=False, ignore_overflow=False,
               err_msg=None):
        """Write ``s``

        :type  s: str|unicode
        :param s: String to write
        :param s_length: Custom length of ``s``
        :param flush: Set this to flush the terminal stream after writing
        :param ignore_overflow: Set this to ignore if s will exceed
            the terminal's width
        :param err_msg: The error message given to WidthOverflowError
            if it is triggered
        """
        if not ignore_overflow:
            s_length = len(s) if s_length is None else s_length
            if err_msg is None:
                err_msg = (
                    "Terminal has {} columns; attempted to write "
                    "a string {} of length {}.".format(
                        self.columns, repr(s), s_length)
                )
            ensure(s_length <= self.columns, WidthOverflowError, err_msg)
        self.cursor.write(s)
        if flush:
            self.cursor.flush()

    def _format_widgets(self):
        result = []
        expanding = []
        width = self.term.width

        for index, widget in enumerate(self.widgets):
            if isinstance(widget, WidgetHFill):
                result.append(widget)
                expanding.insert(0, index)
            else:
                widget = format_updatable(widget, self)
                result.append(widget)
                width -= len(widget)

        count = len(expanding)
        while count:
            portion = max(floor(width * 1. / count), 0)
            index = expanding.pop()
            count -= 1

            widget = result[index].update(self, portion)
            width -= len(widget)
            result[index] = widget

        return result

    def _format_line(self):
        'Joins the widgets and justifies the line'
        widgets = ''.join(self._format_widgets())
        return widgets.ljust(self.term.width)
    ##################
    # Public Methods #
    ##################

    def draw(self, value, newline=True, flush=True):
        """Draw the progress bar

        :type  value: int
        :param value: Progress value relative to ``self.max_value``
        :type  newline: bool
        :param newline: If this is set, a newline will be written after drawing
        """
        # This is essentially winch-handling without having
        #   to do winch-handling; cleanly redrawing on winch is difficult
        #   and out of the intended scope of this class; we *can*
        #   however, adjust the next draw to be proper by re-measuring
        #   the terminal since the code is mostly written dynamically
        #   and many attributes and dynamically calculated properties.
        self._measure_terminal()

        amount_complete = value / self.max_value

        # update value for widgets
        self.finished = amount_complete
        self.currval = value
        now = time()
        self.seconds_elapsed = now - self.start_time

        fill_amount = int(floor(amount_complete * self.max_width))
        empty_amount = self.max_width - fill_amount

        # e.g., '10/20' if 'fraction' or '50%' if 'percentage'
        amount_complete_str = (
            u"{}/{}".format(value, self.max_value)
            if self._num_rep == "fraction" else
            u"{}%".format(int(floor(amount_complete * 100)))
        )

        # Write title if supposed to be above
        if self._title_pos == "above":
            title_str = u"{}{}\n".format(
                " " * self._indent,
                self.title,
            )
            self._write(title_str, ignore_overflow=True)

        # Construct just the progress bar
        bar_str = u''.join([
            u(self.filled(self._filled_char * fill_amount)),
            u(self.empty(self._empty_char * empty_amount)),
        ])
        # Wrap with start and end character
        bar_str = u"{}{}{}".format(self.start_char, bar_str, self.end_char)
        # Add on title if supposed to be on left or right
        if self._title_pos == "left":
            bar_str = u"{} {}".format(self.title, bar_str)
        elif self._title_pos == "right":
            bar_str = u"{} {}".format(bar_str, self.title)
        # Add indent
        # bar_str = u''.join([" " * self._indent, bar_str])
        # Add complete percentage or fraction
        bar_str = u"{} {}".format(bar_str, amount_complete_str)
        # Add the widgets
        bar_str = u"{}   {}".format(bar_str, self._format_line())
        # Set back to normal after printing
        bar_str = u"{}{}".format(bar_str, self.term.normal)
        # Finally, write the completed bar_str
        self._write(bar_str, s_length=self.full_line_width)

        # Write title if supposed to be below
        if self._title_pos == "below":
            title_str = u"\n{}{}".format(
                " " * self._indent,
                self.title,
            )
            self._write(title_str, ignore_overflow=True)

        # Newline to wrap up
        if newline:
            self.cursor.newline()
        if flush:
            self.cursor.flush()
