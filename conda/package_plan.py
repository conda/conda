# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' The PackagePlan module provides the `PackagePlan` class, which encapsulates
executing sets of operations that modify Anaconda environments, as well as functions
for creating PackagePlans for different circumstances.

'''
import logging


from conda.config import Config
from install import make_available, link, unlink
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar
from remote import fetch_file
from package import sort_packages_by_name


__all__ = [
    'PackagePlan'
]


log = logging.getLogger(__name__)


class PackagePlan(object):
    '''
    Encapsulates a package management action, describing all operations to
    take place. Operations include downloading packages from a channel,
    linking and unlinking available packages. Additionally, PackagePlan
    objects report any packages that will be left with unmet dependencies as a
    result of this action.
    '''

    __slots__ = ['downloads', 'activations', 'deactivations', 'broken', 'missing', 'update']

    def __init__(self):
        self.downloads     = set()
        self.activations   = set()
        self.deactivations = set()
        self.broken        = set()
        self.missing       = set()
        self.update       = None

    def execute(self, env, progress_bar=True, channels=None):
        '''
        Perform the operations contained in the package plan

        Parameters
        ----------
        env : :py:class:`Environment <conda.environment.Environment>` object
            Anaconda environment to execute plan in
        progress_bar : bool, optional
            whether to show a progress bar during any downloads

        '''
        if progress_bar:
            download_widgets = [
                '', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ', FileTransferSpeed()
            ]
            download_progress = ProgressBar(widgets=download_widgets)

            package_widgets = ['', ' ', Bar(), ' ', Percentage()]
            package_progress = ProgressBar(widgets=package_widgets)
        else:
            download_progress = None
            package_progress = None

        if not channels:
            conf = Config()
            channels = conf.channel_urls
        self._handle_downloads(env, channels, download_progress)
        self._handle_deactivations(env, package_progress)
        self._handle_activations(env, package_progress)

    def _handle_downloads(self, env, channels, progress):
        if progress and self.downloads:
            print
            print "Fetching packages..."
            print

        for pkg in sorted(self.downloads):
            fetch_file(pkg.filename, channels, md5=pkg.md5,
                       size=pkg.size, progress=progress)
            make_available(env.conda.packages_dir, pkg.canonical_name)

    def _handle_deactivations(self, env, progress):
        if progress and self.deactivations:
            print
            print "Unlinking packages..."
            print
            progress.maxval = len(self.deactivations)
            progress.start()

        for i, pkg in enumerate(sorted(self.deactivations)):
            if progress:
                progress.widgets[0] = '[%-20s]' % pkg.name
                progress.update(i)
            unlink(pkg.canonical_name, env.prefix)

        if progress and self.deactivations:
            progress.widgets[0] = '[      COMPLETE      ]'
            progress.finish()

    def _handle_activations(self, env, progress):
        if progress and self.activations:
            print
            print "Linking packages..."
            print
            progress.maxval = len(self.activations)
            progress.start()

        for i, pkg in enumerate(sorted(self.activations)):
            if progress:
                progress.widgets[0] = '[%-20s]' % pkg.name
                progress.update(i)
            link(env.conda.packages_dir, pkg.canonical_name, env.prefix)

        if progress and self.activations:
            progress.widgets[0] = '[      COMPLETE      ]'
            progress.finish()

    def empty(self):
        ''' Return whether the package plan has any operations to perform or not

        Returns
        -------
        empty bool
            True if the package plan contains no operations to perform
        '''
        return not (self.downloads or self.activations or self.deactivations)

    def __str__(self):
        result = ''
        if self.downloads:
            result += _download_string % self._format_packages(self.downloads, use_channel=True)
        if self.deactivations:
            result += _deactivate_string % self._format_packages(self.deactivations)
        if self.activations:
            result += _activate_string % self._format_packages(self.activations)
        if self.broken:
            result += _broken_string % self._format_packages(self.broken)
        if self.missing:
            result += _missing_string % self._format_packages(self.missing)
        return result

    def _format_packages(self, pkgs, use_channel=False):
        result = ''
        if use_channel:
            for pkg in sort_packages_by_name(pkgs):
                result += '    %s [%s]\n' % (pkg.filename, pkg.channel)
        else:
            result += "    %-25s  |  %-15s\n" % ('package', 'build')
            result += "    %-25s  |  %-15s\n" % ('-'*25, '-'*15)
            for pkg in sort_packages_by_name(pkgs):
                result += '    %-25s  |  %15s\n' % (pkg, pkg.build)
        return result




_download_string = '''
The following packages will be downloaded:

%s
'''

_activate_string = '''
The following packages will be linked:

%s
'''

_deactivate_string = '''
The following packages will be UN-linked:

%s
'''

_broken_string = '''
The following packages will be left with BROKEN dependencies after this operation:

%s
'''

_missing_string = '''
After this operation, the following dependencies will be MISSING:

%s
'''
