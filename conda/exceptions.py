class CondaException(Exception):
    pass


class InvalidInstruction(CondaException):
    def __init__(self, instruction, *args, **kwargs):
        msg = "No handler for instruction: %r" % instruction
        super(InvalidInstruction, self).__init__(msg, *args, **kwargs)


class UnableToWriteToPackage(RuntimeError, CondaException):
    def __init__(self, pkg_name, *args, **kwargs):
        msg = ("Unable to remove files for package: {pkg_name}\n\n"
               "Please close all processes running code from {pkg_name} and "
               "try again.\n".format(pkg_name=pkg_name))
        super(UnableToWriteToPackage, self).__init__(msg, *args, **kwargs)
