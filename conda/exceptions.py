class CondaException(Exception):
    pass


class FileNotFound(CondaException):
    pass


class InvalidInstruction(CondaException):
    def __init__(self, instruction, *args, **kwargs):
        msg = "No handler for instruction: %r" % instruction
        super(InvalidInstruction, self).__init__(msg, *args, **kwargs)
