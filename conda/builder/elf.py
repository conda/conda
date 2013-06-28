from subprocess import call
from distutils.spawn import find_executable
from os.path import islink, isfile


# extensions which are assumed to belong to non-ELF files
NO_EXT = (
    '.py', '.pyc', '.pyo', '.h', '.a', '.c', '.txt', '.html',
    '.xml', '.png', '.jpg', '.gif',
    '.o' # ELF but not what we are looking for
)

MAGIC = '\x7fELF'


def is_elf(path):
    if path.endswith(NO_EXT) or islink(path) or not isfile(path):
        return False
    with open(path, 'rb') as fi:
        head = fi.read(4)
    return bool(head ==  MAGIC)


def chrpath(runpath, path):
    call(['chrpath', '-c', '-r', runpath, path])
