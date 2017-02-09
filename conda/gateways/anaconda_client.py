# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
from glob import glob
from logging import getLogger
from os.path import basename, isdir, isfile, join
from stat import S_IREAD, S_IWRITE

from .disk.delete import rm_rf
from .._vendor.appdirs import AppDirs, EnvAppDirs
from ..common.url import quote_plus, unquote_plus

log = getLogger(__name__)


def replace_first_api_with_conda(url):
    # replace first occurrence of 'api' with 'conda' in url
    return re.sub(r'([./])api([./])', r'\1conda\2', url, count=1)


def _get_binstar_token_directory():
    if 'BINSTAR_CONFIG_DIR' in os.environ:
        return EnvAppDirs('binstar', 'ContinuumIO',
                          os.environ[str('BINSTAR_CONFIG_DIR')]).user_data_dir
    else:
        return AppDirs('binstar', 'ContinuumIO').user_data_dir


def read_binstar_tokens():
    tokens = dict()
    token_dir = _get_binstar_token_directory()
    if not isdir(token_dir):
        return tokens

    token_files = glob(join(token_dir, '*.token'))
    for tkn_file in token_files:
        url = re.sub(r'\.token$', '', unquote_plus(basename(tkn_file)))
        with open(tkn_file) as f:
            token = f.read()
        tokens[url] = tokens[replace_first_api_with_conda(url)] = token
    return tokens


def set_binstar_token(url, token):
    token_dir = _get_binstar_token_directory()
    if not isdir(token_dir):
        os.makedirs(token_dir)

    tokenfile = join(token_dir, '%s.token' % quote_plus(url))

    if isfile(tokenfile):
        os.unlink(tokenfile)
    with open(tokenfile, 'w') as fd:
        fd.write(token)
    os.chmod(tokenfile, S_IWRITE | S_IREAD)


def remove_binstar_token(url):
    token_dir = _get_binstar_token_directory()
    tokenfile = join(token_dir, '%s.token' % quote_plus(url))
    rm_rf(tokenfile)


if __name__ == "__main__":
    print(read_binstar_tokens())
