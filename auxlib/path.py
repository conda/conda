# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import
from distutils.sysconfig import get_python_lib
from logging import getLogger
from os import chdir, getcwd
from os.path import (abspath, dirname, exists, expanduser, expandvars, isdir, isfile, join,
                     normpath, sep)
try:
    import pkg_resources
except ImportError:
    pkg_resources = None
import sys

log = getLogger(__name__)


ROOT_PATH = abspath(sep)


def site_packages_paths():
    if hasattr(sys, 'real_prefix'):
        # in a virtualenv
        log.debug('searching virtualenv')
        return [p for p in sys.path if p.endswith('site-packages')]
    else:
        # not in a virtualenv
        log.debug('searching outside virtualenv')  # pragma: no cover
        return [get_python_lib()]  # pragma: no cover


class PackageFile(object):

    def __init__(self, file_path, package_name):
        self.file_path = file_path
        self.package_name = package_name

    def __enter__(self):
        self.file_handle = open_package_file(self.file_path, self.package_name)
        return self.file_handle

    def __exit__(self, *args):
        self.file_handle.close()


class ChangePath(object):

    def __init__(self, path):
        self.dirpath = dirname(path) if isfile(path) else path
        if not isdir(self.dirpath):
            raise IOError('File or directory not found: {0}'.format(path))

    def __enter__(self):
        self.cwd = getcwd()
        chdir(self.dirpath)
        return self

    def __exit__(self, *args):
        chdir(self.cwd)


def open_package_file(file_path, package_name):
    file_path = expand(file_path)

    # look for file at relative path
    if exists(file_path):
        log.info("found real file {0}".format(file_path))
        return open(file_path)

    # look for file in package resources
    if (package_name and pkg_resources is not None and
            pkg_resources.resource_exists(package_name, file_path)):
        log.info("found package resource file {0} for package {1}".format(file_path, package_name))
        return pkg_resources.resource_stream(package_name, file_path)

    # look for file in site-packages
    package_path = find_file_in_site_packages(file_path, package_name)
    if package_path:
        return open(package_path)  # pragma: no cover

    msg = "file for module [{0}] cannot be found at path {1}".format(package_name, file_path)
    log.error(msg)
    raise IOError(msg)


def find_file_in_site_packages(file_path, package_name):
    package_path = package_name.replace('.', '/')
    for site_packages_path in site_packages_paths():
        test_path = join(site_packages_path, package_path, file_path)
        if exists(test_path):
            log.info("found site-package file {0} for package {1}".format(file_path, package_name))
            return test_path
        else:
            log.error("No file found at {0}.".format(test_path))
    return None


def expand(path):
    return normpath(expanduser(expandvars(path)))


def absdirname(path):
    return abspath(expanduser(dirname(path)))
