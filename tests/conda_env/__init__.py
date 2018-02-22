from os.path import dirname, join


def support_file(filename):
    return join(dirname(__file__), 'support', filename)
