# TODO: Conda should be refactored to include this object

class Spec(object):
    def __init__(self, spec_str):
        if '/' in spec_str:
            self.username, spec_str = spec_str.split('/', 1)
        else:
            self.username = None

        if '==' in spec_str:
            self.package_name, self.version_required = spec_str.split('==', 1)
        else:
            self.package_name = spec_str
            self.version_required = None

    def __str__(self):
        return ('<Spec: username=%(username)r '
                'package_name=%(package_name)r '
                'version_required=%(version_required)r>' % self.__dict__)
