def get_noarch_cls(noarch_type):
    return NOARCH_CLASSES.get(str(noarch_type).lower(), NoArch) if noarch_type else None


class NoArch(object):

    def link(self):
        pass

    def unlink(self):
        pass


class NoArchPython(NoArch):

    def link(self):
        # map directories (site-packages)
        # deal with setup.py scripts
        # deal with entry points
        # compile pyc files
        pass

    def unlink(self):
        pass


NOARCH_CLASSES = {
    'python': NoArchPython,
    True: NoArch,
}








