# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import json
import os
import platform
import sys
from os.path import abspath, exists, expanduser, join
from urllib2 import urlopen

from conda.constraints import AllOf, Requires, Satisfies
from conda.package_index import PackageIndex
from conda.package_spec import PackageSpec
from conda.install import make_available, link
from conda.remote import fetch_file


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'init',
        description = "Bootstrap Anaconda installation.",
        help        = "Bootstrap Anaconda installation.",
    )
    p.add_argument(
        '-p', "--prefix",
        action  = "store",
        help    = "directory to install Anaconda into",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    if not args.prefix:
        raise RuntimeError("Must provide directory location to install into.")

    prefix = abspath(expanduser(args.prefix))

    if exists(prefix):
        raise RuntimeError("Install directory '%s' already exists." % prefix)

    os.mkdir(prefix)
    subdirs = ["bin",  "conda-meta",  "docs",  "envs",  "include",  "lib",  "pkgs",  "python.app",  "share",]
    for sd in subdirs:
        os.mkdir("%s/%s" % (prefix, sd))

    channel = "http://repo.continuum.io/pkgs/free/%s/" % get_platform()

    index = PackageIndex(fetch_index(channel))

    py_spec     = PackageSpec("python 2.7")
    yaml_spec   = PackageSpec("yaml")
    pyyaml_spec = PackageSpec("pyyaml")
    conda_spec  = PackageSpec("conda")

    py = max(index.find_matches(Satisfies(py_spec)))
    yaml = max(index.find_matches(Satisfies(yaml_spec)))
    pyyaml = max(index.find_matches(AllOf(Requires(py_spec), Satisfies(pyyaml_spec))))
    conda = max(index.find_matches(AllOf(Requires(py_spec), Satisfies(conda_spec))))

    pkgs_dir = join(prefix, 'pkgs')
    pkgs = [py, yaml, pyyaml, conda]

    for pkg in pkgs:
        fetch_file(pkg.filename, [channel], md5=pkg.md5, size=pkg.size, pkgs_dir=pkgs_dir)
        make_available(pkgs_dir, pkg.canonical_name)
        link(pkgs_dir, pkg.canonical_name, prefix)

    if exists(prefix):
        print "Anaconda installed into directory '%s'" % prefix

def fetch_index(url):
    try:
        fi = urlopen(url + 'repodata.json')
        repodata = json.loads(fi.read())
    except IOError:
        raise RuntimeError("Failed to fetch index for channel '%s' (bad url or network issue?)" % url)

    fi.close()

    index = repodata['packages']

    for pkg_info in index.itervalues():
        pkg_info['channel'] = url

    return index

def get_platform():
    sys_map = {'linux2': 'linux', 'darwin': 'osx', 'win32': 'win'}
    bits = int(platform.architecture()[0][:2])
    system = sys_map.get(sys.platform, 'unknown')
    return '%s-%d' % (system, bits)
