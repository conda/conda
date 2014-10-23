import pkg_resources

ENTRY_POINT = 'conda.env.installers'


class InvalidInstaller(Exception):
    def __init__(self, name):
        msg = 'Unable to load installer for {}'.format(name)
        super(InvalidInstaller, self).__init__(msg)


def get_installer(name):
    for entry_point in pkg_resources.iter_entry_points(ENTRY_POINT):
        if entry_point.name == name:
            return entry_point.load()

    raise InvalidInstaller(name)
