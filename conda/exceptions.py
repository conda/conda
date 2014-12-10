class CondaException(Exception):
    pass


class InvaidInstruction(CondaException):
    def __init__(self, instruction, *args, **kwargs):
        msg = "No handler for instruction: %r" % instruction
        super(InvaidInstruction, self).__init__(msg, *args, **kwargs)
