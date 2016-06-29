from __future__ import absolute_import, division, print_function

class CondaException(Exception):
    pass


class InvalidInstruction(CondaException):
    def __init__(self, instruction, *args, **kwargs):
        msg = "No handler for instruction: %r" % instruction
        super(InvalidInstruction, self).__init__(msg, *args, **kwargs)
