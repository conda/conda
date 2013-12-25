"""
Tools for converting CRAN R packages to conda recipes.
"""
#===============================================================================
# Imports
#===============================================================================
from __future__ import division, absolute_import

import os
import sys
from os.path import join, isdir, exists, isfile

from conda.fetch import download

from conda.builder.r import (
    RPackage,
    RVersionDependencyMismatch,
)

#===============================================================================
# Globals
#===============================================================================
DEFAULT_CRAN_URL = 'http://cran.r-project.org/src/contrib'

#===============================================================================
# Helpers
#===============================================================================
def cran_url_to_src_contrib_url(cran_url):
    trailing_slash = True if cran_url[-1] == '/' else False
    maybe_slash = '/' if not trailing_slash else ''
    suffix = 'src/contrib' + ('/' if trailing_slash else '')
    if not cran_url.endswith(suffix):
        src_contrib_url = cran_url + maybe_slash + suffix
    else:
        src_contrib_url = cran_url + maybe_slash
    return src_contrib_url

def reduce_package_line_continuations(chunk):
    """
    >>> chunk = [
        'Package: A3',
        'Version: 0.9.2',
        'Depends: R (>= 2.15.0), xtable, pbapply',
        'Suggests: randomForest, e1071',
        'Imports: MASS, R.methodsS3 (>= 1.5.2), R.oo (>= 1.15.8), R.utils (>=',
        '        1.27.1), matrixStats (>= 0.8.12), R.filesets (>= 2.3.0), ',
        '        sampleSelection, scatterplot3d, strucchange, systemfit',
        'License: GPL (>= 2)',
        'NeedsCompilation: no']
    >>> reduce_package_line_continuations(chunk)
    ['Package: A3',
     'Version: 0.9.2',
     'Depends: R (>= 2.15.0), xtable, pbapply',
     'Suggests: randomForest, e1071',
     'Imports: MASS, R.methodsS3 (>= 1.5.2), R.oo (>= 1.15.8), R.utils (>= 1.27.1), matrixStats (>= 0.8.12), R.filesets (>= 2.3.0), sampleSelection, scatterplot3d, strucchange, systemfit, rgl,'
     'License: GPL (>= 2)',
     'NeedsCompilation: no']
    """
    # According to the debian deb822 spec, which R is based off, a continuation
    # is any line that starts with either whitespace or a tab.  In the case of
    # the CRAN PACKAGES file though, all continuations are indented with 8
    # spaces.
    continuation = ' ' * 8
    continued_ix = None
    continued_line = None
    had_continuation = False
    accumulating_continuations = False

    for (i, line) in enumerate(chunk):
        if line.startswith(continuation):
            line = line.replace(continuation, ' ')
            if accumulating_continuations:
                assert had_continuation
                continued_line += line
                chunk[i] = None
            else:
                accumulating_continuations = True
                continued_ix = i-1
                continued_line = chunk[continued_ix] + line
                had_continuation = True
                chunk[i] = None
        else:
            if accumulating_continuations:
                assert had_continuation
                chunk[continued_ix] = continued_line
                accumulating_continuations = False
                continued_line = None
                continued_ix = None

    if had_continuation:
        # Remove the None(s).
        chunk = [ c for c in chunk if c ]

    return chunk

#===============================================================================
# Classes
#===============================================================================

class CranPackages(object):
    # I'm currently using this class in an exploratory-development fashion via
    # an interactive IPython session. It'll eventually be hooked into the CLI.

    def __init__(self, cran_url, output_dir):
        self.src_contrib_url = cran_url_to_src_contrib_url(cran_url)
        self.output_dir = output_dir
        self.packages_url = self.src_contrib_url + '/PACKAGES'
        self.packages_file = join(output_dir, 'PACKAGES')
        self.packages_json = self.packages_file + '.json'

        self.lines = None
        self.chunks = None
        self.rpackages = []

    def create_or_update_conda_recipes_for_cran_r_packages(self):
        if not exists(self.packages_file):
            self._download()

        self._read_packages_file()
        self._load_rpackages()
        self._persist_rpackages()

    def _download(self):
        download(self.packages_url, self.packages_file)

    def _read_packages_file(self):
        with open(self.packages_file, 'r') as f:
            data = f.read()
        lines = data.splitlines()
        chunk = []
        chunks = []
        for line in lines:
            if not line:
                chunks.append(reduce_package_line_continuations(chunk))
                chunk = []
            else:
                chunk.append(line)

        self.lines = lines
        self.chunks = chunks

    def _load_rpackages(self):
        assert self.chunks, "did you forget to call _read_packages_file()?"
        base_url = self.src_contrib_url
        output_dir = self.output_dir
        for lines in self.chunks:
            try:
                self.rpackages.append(RPackage(lines, base_url, output_dir))
            except RVersionDependencyMismatch:
                # The package depends on a version of R different from ours.
                # (We'll eventually handle this via conda version management;
                # much like we do for multiple Python versions/dependencies.)
                continue

    def _persist_rpackages(self):
        assert self.rpackages, "did you forget to call _load_rpackages()?"
        for rpkg in self.rpackages:
            rpkg.persist()

    def _find_unique_package_description_keys(self):
        """
        Helper method that enumerates all lines in PACKAGES and finds the
        unique keys used to describe packages.  i.e. given:

            ['Package: A3',
             'Version: 0.9.2',
             'Depends: R (>= 2.15.0), xtable, pbapply',
             'Suggests: randomForest, e1071',
             'License: GPL (>= 2)',
             'NeedsCompilation: no']

        This will return 'Package', 'Version', etc.
        """
        seen = set()
        for chunk in self.chunks:
            for line in chunk:
                if not line:
                    continue
                (key, value) = line.split(': ')
                seen.add(key)

        return sorted(seen)

#===============================================================================
# Main
#===============================================================================
def main(args, parser):
    pass

# vim:set ts=8 sw=4 sts=4 tw=78 et:
