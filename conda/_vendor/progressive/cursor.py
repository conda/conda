import os

from .blessings import Terminal


class Cursor(object):
    """Common methods for cursor manipulation

    :type  term: NoneType|blessings.Terminal
    :param term: Terminal instance; if not given, will be created by the class
    """

    def __init__(self, term=None):
        self.term = Terminal() if term is None else term
        self._stream = self.term.stream
        self._saved = False

    def write(self, s):
        """Writes ``s`` to the terminal output stream

        Writes can be disabled by setting the environment variable
            `PROGRESSIVE_NOWRITE` to `'True'`
        """
        should_write_s = os.getenv('PROGRESSIVE_NOWRITE') != "True"
        if should_write_s:
            self._stream.write(s)

    def save(self):
        """Saves current cursor position, so that it can be restored later"""
        self.write(self.term.save)
        self._saved = True

    def restore(self):
        """Restores cursor to the previously saved location

        Cursor position will only be restored IF it was previously saved
            by this instance (and not by any external force)
        """
        if self._saved:
            self.write(self.term.restore)

    def flush(self):
        """Flush buffer of terminal output stream"""
        self._stream.flush()

    def newline(self):
        """Effects a newline by moving the cursor down and clearing"""
        self.write(self.term.move_down)
        self.write(self.term.clear_bol)

    def clear_lines(self, num_lines=0):
        for i in range(num_lines):
            self.write(self.term.clear_eol)
            self.write(self.term.move_down)
        for i in range(num_lines):
            self.write(self.term.move_up)
