import os


def support_file(filename):
    return os.path.join(os.path.dirname(__file__), '../support', filename)
