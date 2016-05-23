# -*- coding: utf-8 -*-
#!/usr/bin/env python
from __future__ import absolute_import, division, print_function
import hashlib
import json
import logging
import logging.handlers
import os
import shutil
import sys
import tempfile
import urllib
import urllib2


def init_logging():
    log_formatter = logging.Formatter("ttam[%(name)s] [%(levelname)s]: %(message)s")

    root = logging.getLogger()
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(log_formatter)
    root.addHandler(stdout_handler)

    set_logger()


def set_logger(logger_name=None, level=logging.INFO):
    global log
    log = logging.getLogger() if logger_name is None else logging.getLogger(logger_name)
    log.setLevel(level)

log = None
init_logging()


def expand(*path):
    joined = os.path.join(*path)
    return os.path.normpath(os.path.expanduser(os.path.expandvars(joined)))


def get_remote_md5_sum(url, max_file_size=100*1024*1024):
    remote = urllib2.urlopen(url)
    hash = hashlib.md5()
    total_read = 0
    while True:
        data = remote.read(4096)
        total_read += 4096
        if not data or total_read > max_file_size:
            break
        hash.update(data)
    return hash.hexdigest()


class IntegrityError(Exception):
    def __init__(self, message):
        super(IntegrityError, self).__init__(message)
        log.error("REPO INTEGRITY ERROR: {0}".format(message))


class Repo(object):

    REPOS = {
        'default': {
            'url': 'https://repo.continuum.io/pkgs/free',
            'architectures': [
                'linux-64'
            ],
        }
    }

    def __init__(self, repo_name, local_base_path="~/repo"):
        self.local_path = expand(local_base_path)
        self.repo_name = repo_name
        self.base_url = Repo.REPOS[repo_name]['url']
        self.architectures = Repo.REPOS[repo_name]['architectures']

    def update(self):
        log.info("Beginning clone of repo {0} at {1}."
                 "".format(self.base_url, expand(self.local_path, self.repo_name)))
        for arch in self.architectures:
            directory = expand(self.local_path, self.repo_name, arch)
            if not os.path.exists(directory):
                os.makedirs(directory, 02775)
            os.chdir(directory)
            if not self._update_is_needed(arch):
                log.info("Directory {0} is up-to-date.".format(directory))
                continue
            self._update_directory(arch)
            self._integrity_check(arch)
        log.info("Clone of {0} complete.".format(self.repo_name))

    def _update_is_needed(self, arch):
        try:
            with open("repodata.json.bz2", 'rb') as f:
                local_hash = hashlib.md5(f.read()).hexdigest()
        except IOError:
            local_hash = None
        remote_hash = get_remote_md5_sum("{0}/{1}/repodata.json.bz2".format(self.base_url, arch))
        return local_hash != remote_hash

    def _get_remote_repodata(self, arch):
        with tempfile.NamedTemporaryFile(delete=False) as tfile:
            url = "{0}/{1}/repodata.json".format(self.base_url, arch)
            log.debug("Downloading {0} to {1}".format(url, os.getcwd()))
            response = urllib2.urlopen(url)
            tfile.write(response.read())
        with open(tfile.name, 'r') as f:
            remote_data = json.loads(f.read())
        return tfile.name, remote_data

    def _get_local_repodata(self):
        try:
            with open('repodata.json', 'r') as f:
                return json.loads(f.read())
        except IOError:
            return dict(packages={})

    def _download(self, filename, arch, expected_hash):
        url = "{0}/{1}/{2}".format(self.base_url, arch, filename)
        log.debug("Downloading {0} to {1}".format(url, os.getcwd()))
        urllib.urlretrieve(url, filename)
        actual_hash = hashlib.md5(open(filename, 'rb').read()).hexdigest()
        if expected_hash is not None and actual_hash != expected_hash:
            raise IOError(filename)
        return actual_hash

    def _update_directory(self, arch):
        remote_data_filename, remote_data = self._get_remote_repodata(arch)

        local_data = self._get_local_repodata()
        local_packages = set(local_data['packages'].keys())
        remote_packages = set(remote_data['packages'].keys())

        remove_these = local_packages - remote_packages
        download_these = remote_packages - local_packages

        # overwrite any packages
        matched_names = local_packages.intersection(remote_packages)
        for package_name in matched_names:
            local_md5 = local_data.get('packages', {}).get(package_name, {}).get('md5', None)
            if local_md5 != remote_data['packages'][package_name]['md5']:
                download_these.add(package_name)

        log.info("Downloading {0} packages to directory {1}"
                 "".format(len(download_these), os.getcwd()))

        for filename in download_these:
            expected_hash = remote_data['packages'][filename]['md5']
            self._download(filename, arch, expected_hash)

        for filename in remove_these:
            log.debug("Removing file {0}".format(expand(os.getcwd(), filename)))
            os.remove(filename)

        self._download("repodata.json.bz2", arch, None)
        shutil.copy2(remote_data_filename, "repodata.json")
        os.remove(remote_data_filename)

    def _integrity_check(self, arch):
        urllib.urlcleanup()
        log.debug("Comparing md5 hashes to check file integrity.")

        # check hashes for repo data files
        data_file_names = set(['repodata.json', 'repodata.json.bz2'])
        for filename in data_file_names:
            remote_hash = get_remote_md5_sum("{0}/{1}/{2}".format(self.base_url, arch, filename))
            self._itegrity_check_file(filename, remote_hash)

        local_data = self._get_local_repodata()

        # check that files were properly removed
        correct_file_list = set(local_data['packages'].keys())
        listdir_results = set(os.listdir(os.getcwd()))
        left_over_files = listdir_results.symmetric_difference(correct_file_list | data_file_names)
        if len(left_over_files) != 0:
            raise IntegrityError("Files exist that should have been removed. {0}"
                                 "".format(list(left_over_files)))

        # check hashes for package files
        for filename in correct_file_list:
            expected_md5 = local_data['packages'][filename]['md5']
            self._itegrity_check_file(filename, expected_md5)

    def _itegrity_check_file(self, filename, hash):
        with open(filename, 'rb') as f:
            read_hash = hashlib.md5(f.read()).hexdigest()
        if read_hash != hash:
            raise IntegrityError("MD5 mismatch for {0}/{1}\n"
                                 "Expected [{2}]\n"
                                 "Got      [{3}]".format(os.getcwd(), filename, hash, read_hash))


def main():
    try:
        set_logger("repo-clone", logging.DEBUG)
        repo_name = sys.argv[1] if len(sys.argv) >=2 else 'default'
        Repo(repo_name).update()
        return 0
    except IntegrityError:
        return 4
    except Exception as e:
        log.exception("Uncaught exception [{0}]".format(e.message))
        return 1


if __name__ == '__main__':
    sys.exit(main())
