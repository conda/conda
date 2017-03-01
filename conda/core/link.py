# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from logging import getLogger
import os
from os.path import dirname, join
from subprocess import CalledProcessError
import sys
from traceback import format_exc
import warnings

from .linked_data import (get_python_version_for_prefix, linked_data as get_linked_data,
                          load_meta)
from .package_cache import PackageCache
from .path_actions import (CompilePycAction, CreateApplicationEntryPointAction,
                           CreateLinkedPackageRecordAction, CreateNonadminAction,
                           CreatePrivateEnvMetaAction, CreatePythonEntryPointAction,
                           LinkPathAction, MakeMenuAction, RemoveLinkedPackageRecordAction,
                           RemoveMenuAction, RemovePrivateEnvMetaAction, UnlinkPathAction)
from .. import CondaError, CondaMultiError
from .._vendor.auxlib.collection import first
from .._vendor.auxlib.ish import dals
from ..base.context import context
from ..common.compat import ensure_text_type, iteritems, itervalues, on_win, text_type
from ..common.path import (explode_directories, get_all_directories, get_bin_directory_short_path,
                           get_major_minor_version,
                           get_python_site_packages_short_path)
from ..exceptions import (KnownPackageClobberError, LinkError, SharedLinkPathClobberError,
                          UnknownPackageClobberError, maybe_raise)
from ..gateways.disk.create import mkdir_p
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.read import isdir, isfile, lexists, read_package_info
from ..gateways.disk.test import hardlink_supported, softlink_supported
from ..gateways.subprocess import subprocess_call
from ..models.dist import Dist
from ..models.enums import LinkType

try:
    from cytoolz.itertoolz import concat, concatv, groupby
except ImportError:
    from .._vendor.toolz.itertoolz import concat, concatv, groupby  # NOQA

log = getLogger(__name__)


def determine_link_type(extracted_package_dir, target_prefix):
    source_test_file = join(extracted_package_dir, 'info', 'index.json')
    if context.always_copy:
        return LinkType.copy
    if context.always_softlink:
        return LinkType.softlink
    if hardlink_supported(source_test_file, target_prefix):
        return LinkType.hardlink
    if context.allow_softlinks and softlink_supported(source_test_file, target_prefix):
        return LinkType.softlink
    return LinkType.copy


def make_unlink_actions(transaction_context, target_prefix, linked_package_data):
    # no side effects in this function!
    unlink_path_actions = tuple(UnlinkPathAction(transaction_context, linked_package_data,
                                                 target_prefix, trgt)
                                for trgt in linked_package_data.files)

    remove_menu_actions = RemoveMenuAction.create_actions(transaction_context,
                                                          linked_package_data,
                                                          target_prefix)

    meta_short_path = '%s/%s' % ('conda-meta', Dist(linked_package_data).to_filename('.json'))
    remove_conda_meta_actions = (RemoveLinkedPackageRecordAction(transaction_context,
                                                                 linked_package_data,
                                                                 target_prefix, meta_short_path),)

    _all_d = get_all_directories(axn.target_short_path for axn in unlink_path_actions)
    all_directories = sorted(explode_directories(_all_d, already_split=True), reverse=True)
    directory_remove_actions = tuple(UnlinkPathAction(transaction_context, linked_package_data,
                                                      target_prefix, d, LinkType.directory)
                                     for d in all_directories)

    if linked_package_data.preferred_env is not None:
        app_entry_point_short_path = os.path.join(get_bin_directory_short_path(),
                                                  linked_package_data.name)
        unlink_app_entry_point = UnlinkPathAction(transaction_context, linked_package_data,
                                                  context.root_prefix, app_entry_point_short_path),
        unlink_path_actions = unlink_path_actions + unlink_app_entry_point
        private_envs_meta_action = RemovePrivateEnvMetaAction(
            transaction_context, linked_package_data, target_prefix),
    else:
        private_envs_meta_action = ()

    return tuple(concatv(
        remove_menu_actions,
        unlink_path_actions,
        directory_remove_actions,
        private_envs_meta_action,
        remove_conda_meta_actions,
    ))


class UnlinkLinkTransaction(object):

    @classmethod
    def create_from_dists(cls, index, target_prefix, unlink_dists, link_dists):
        # This constructor method helps to patch into the 'plan' framework
        linked_packages_data_to_unlink = tuple(load_meta(target_prefix, dist)
                                               for dist in unlink_dists)

        log.debug("instantiating UnlinkLinkTransaction with\n"
                  "  target_prefix: %s\n"
                  "  unlink_dists:\n"
                  "    %s\n"
                  "  link_dists:\n"
                  "    %s\n",
                  target_prefix,
                  '\n    '.join(text_type(d) for d in unlink_dists),
                  '\n    '.join(text_type(d) for d in link_dists))

        pkg_dirs_to_link = tuple(PackageCache.get_entry_to_link(dist).extracted_package_dir
                                 for dist in link_dists)
        assert all(pkg_dirs_to_link)
        packages_info_to_link = tuple(read_package_info(index[dist], pkg_dir)
                                      for dist, pkg_dir in zip(link_dists, pkg_dirs_to_link))

        return UnlinkLinkTransaction(target_prefix, linked_packages_data_to_unlink,
                                     packages_info_to_link)

    def __init__(self, target_prefix, linked_packages_data_to_unlink, packages_info_to_link):
        # type: (str, Sequence[Dist], Sequence[PackageInfo]) -> NoneType
        # order of unlink_dists and link_dists will be preserved throughout
        #   should be given in dependency-sorted order

        self.target_prefix = target_prefix
        self.linked_packages_data_to_unlink = linked_packages_data_to_unlink
        self.packages_info_to_link = packages_info_to_link

        self._prepared = False
        self._verified = False

    def prepare(self):
        if self._prepared:
            return

        # gather information from disk and caches
        self.prefix_linked_data = get_linked_data(self.target_prefix)
        link_types = tuple(determine_link_type(pkg_info.extracted_package_dir, self.target_prefix)
                           for pkg_info in self.packages_info_to_link)

        # make all the path actions
        # no side effects allowed when instantiating these action objects
        transaction_context = dict()
        python_version = self.get_python_version(self.target_prefix,
                                                 self.linked_packages_data_to_unlink,
                                                 self.packages_info_to_link)
        transaction_context['target_python_version'] = python_version
        sp = get_python_site_packages_short_path(python_version)
        transaction_context['target_site_packages_short_path'] = sp

        unlink_actions = tuple((lnkd_pkg_data, make_unlink_actions(transaction_context,
                                                                   self.target_prefix,
                                                                   lnkd_pkg_data))
                               for lnkd_pkg_data in self.linked_packages_data_to_unlink)

        link_actions = (
            (pkg_info, self.make_link_actions(transaction_context, pkg_info,
                                              self.target_prefix, lt))
            for pkg_info, lt in zip(self.packages_info_to_link, link_types)
        )

        self.all_actions = tuple(per_pkg_actions for per_pkg_actions in
                                 concatv(unlink_actions, link_actions))
        # type: Tuple[pkg_data, Tuple[PathAction]]

        self.num_unlink_pkgs = len(unlink_actions)

        self._prepared = True

    @staticmethod
    def _verify_individual_level(all_actions):
        # run all per-action verify methods
        #   one of the more important of these checks is to verify that a file listed in
        #   the packages manifest (i.e. info/files) is actually contained within the package
        for _, pkg_actions in all_actions:
            for axn in pkg_actions:
                if axn.verified:
                    continue
                error_result = axn.verify()
                if error_result:
                    log.debug("Verification error in action %s", axn)
                    log.debug(format_exc())
                    yield error_result

    @staticmethod
    def _verify_transaction_level(target_prefix, all_actions, num_unlink_pkgs):
        # further verification of the whole transaction
        # for each path we are creating in link_actions, we need to make sure
        #   1. each path either doesn't already exist in the prefix, or will be unlinked
        #   2. there's only a single instance of each path

        # paths are case-insensitive on windows apparently
        lower_on_win = lambda p: p.lower() if on_win else p
        unlink_paths = set(lower_on_win(axn.target_short_path)
                           for _, pkg_actions in all_actions[:num_unlink_pkgs]
                           for axn in pkg_actions
                           if isinstance(axn, UnlinkPathAction))
        # we can get all of the paths being linked by looking only at the
        #   CreateLinkedPackageRecordAction actions
        create_lpr_actions = (axn
                              for _, pkg_actions in all_actions[num_unlink_pkgs:]
                              for axn in pkg_actions
                              if isinstance(axn, CreateLinkedPackageRecordAction))

        link_paths_dict = defaultdict(list)
        for axn in create_lpr_actions:
            for path in axn.linked_package_record.files:
                path = lower_on_win(path)
                link_paths_dict[path].append(axn)
                if path not in unlink_paths and lexists(join(target_prefix, path)):
                    # we have a collision; at least try to figure out where it came from
                    linked_data = get_linked_data(target_prefix)
                    colliding_linked_package_record = first(
                        (lpr for lpr in itervalues(linked_data)),
                        key=lambda lpr: path in lpr.files
                    )
                    if colliding_linked_package_record:
                        yield KnownPackageClobberError(Dist(axn.linked_package_record), path,
                                                       Dist(colliding_linked_package_record),
                                                       context)
                    else:
                        yield UnknownPackageClobberError(Dist(axn.linked_package_record), path,
                                                         context)
        for path, axns in iteritems(link_paths_dict):
            if len(axns) > 1:
                yield SharedLinkPathClobberError(
                    path, tuple(Dist(axn.linked_package_record) for axn in axns), context
                )

    def verify(self):
        if not self._prepared:
            self.prepare()

        exceptions = tuple(exc for exc in concatv(
            self._verify_individual_level(self.all_actions),
            self._verify_transaction_level(self.target_prefix, self.all_actions,
                                           self.num_unlink_pkgs),
        ) if exc)

        if exceptions:
            maybe_raise(CondaMultiError(exceptions), context)
        else:
            log.info(exceptions)

        self._verified = True

    def execute(self):
        if not self._verified:
            self.verify()

        # make sure prefix directory exists
        if not isdir(self.target_prefix):
            try:
                mkdir_p(self.target_prefix)
            except (IOError, OSError) as e:
                log.debug(repr(e))
                raise CondaError("Unable to create prefix directory '%s'.\n"
                                 "Check that you have sufficient permissions."
                                 "" % self.target_prefix)

        pkg_idx = 0
        try:
            for pkg_idx, (pkg_data, actions) in enumerate(self.all_actions):
                self._execute_actions(self.target_prefix, self.num_unlink_pkgs, pkg_idx,
                                      pkg_data, actions)
        except Exception as execute_multi_exc:
            # reverse all executed packages except the one that failed
            rollback_excs = []
            if context.rollback_enabled:
                failed_pkg_idx = pkg_idx
                reverse_actions = self.all_actions[:failed_pkg_idx]
                for pkg_idx, (pkg_data, actions) in reversed(tuple(enumerate(reverse_actions))):
                    excs = self._reverse_actions(self.target_prefix, self.num_unlink_pkgs,
                                                 pkg_idx, pkg_data, actions)
                    rollback_excs.extend(excs)

            raise CondaMultiError(tuple(concatv(
                (execute_multi_exc.errors
                 if isinstance(execute_multi_exc, CondaMultiError)
                 else (execute_multi_exc,)),
                rollback_excs,
            )))

        else:
            for pkg_idx, (pkg_data, actions) in enumerate(self.all_actions):
                for axn_idx, action in enumerate(actions):
                    action.cleanup()

    @staticmethod
    def _execute_actions(target_prefix, num_unlink_pkgs, pkg_idx, pkg_data, actions):
        axn_idx, action, is_unlink = 0, None, True
        try:
            dist = Dist(pkg_data)
            is_unlink = pkg_idx <= num_unlink_pkgs - 1
            if is_unlink:
                log.info("===> UNLINKING PACKAGE: %s <===\n"
                         "  prefix=%s\n",
                         dist, target_prefix)

            else:
                log.info("===> LINKING PACKAGE: %s <===\n"
                         "  prefix=%s\n"
                         "  source=%s\n",
                         dist, target_prefix, pkg_data.extracted_package_dir)

            run_script(target_prefix if is_unlink else pkg_data.extracted_package_dir,
                       Dist(pkg_data),
                       'pre-unlink' if is_unlink else 'pre-link',
                       target_prefix)
            for axn_idx, action in enumerate(actions):
                action.execute()
            run_script(target_prefix, Dist(pkg_data), 'post-unlink' if is_unlink else 'post-link')
        except Exception as e:  # this won't be a multi error
            # reverse this package
            log.debug("Error in action #%d for pkg_idx #%d %r", axn_idx, pkg_idx, action)
            log.debug(format_exc())
            reverse_excs = ()
            if context.rollback_enabled:
                log.error("An error occurred while %s package '%s'.\n"
                          "%r\n"
                          "Attempting to roll back.\n",
                          'uninstalling' if is_unlink else 'installing', Dist(pkg_data), e)
                reverse_excs = UnlinkLinkTransaction._reverse_actions(
                    target_prefix, num_unlink_pkgs, pkg_idx, pkg_data, actions,
                    reverse_from_idx=axn_idx
                )
            raise CondaMultiError(tuple(concatv(
                (e,),
                reverse_excs,
            )))

    @staticmethod
    def _reverse_actions(target_prefix, num_unlink_pkgs, pkg_idx, pkg_data, actions,
                         reverse_from_idx=-1):
        # reverse_from_idx = -1 means reverse all actions
        dist = Dist(pkg_data)
        is_unlink = pkg_idx <= num_unlink_pkgs - 1
        if is_unlink:
            log.info("===> REVERSING PACKAGE UNLINK: %s <===\n"
                     "  prefix=%s\n",
                     dist, target_prefix)

        else:
            log.info("===> REVERSING PACKAGE LINK: %s <===\n"
                     "  prefix=%s\n",
                     dist, target_prefix)
        log.debug("reversing pkg_idx #%d from axn_idx #%d", pkg_idx, reverse_from_idx)

        exceptions = []
        reverse_actions = actions if reverse_from_idx < 0 else actions[:reverse_from_idx+1]
        for axn_idx, action in reversed(tuple(enumerate(reverse_actions))):
            try:
                action.reverse()
            except Exception as e:
                log.debug("action.reverse() error in action #%d for pkg_idx #%d %r", axn_idx,
                          pkg_idx, action)
                log.debug(format_exc())
                exceptions.append(e)
        return exceptions

    @staticmethod
    def get_python_version(target_prefix, linked_packages_data_to_unlink, packages_info_to_link):
        # this method determines the python version that will be present at the
        # end of the transaction
        linking_new_python = next((package_info for package_info in packages_info_to_link
                                   if package_info.index_json_record.name == 'python'),
                                  None)
        if linking_new_python:
            # is python being linked? we're done
            full_version = linking_new_python.index_json_record.version
            assert full_version
            return get_major_minor_version(full_version)

        # is python already linked and not being unlinked? that's ok too
        linked_python_version = get_python_version_for_prefix(target_prefix)
        if linked_python_version:
            find_python = (lnkd_pkg_data for lnkd_pkg_data in linked_packages_data_to_unlink
                           if lnkd_pkg_data.name == 'python')
            unlinking_this_python = next(find_python, None)
            if unlinking_this_python is None:
                # python is not being unlinked
                return linked_python_version

        # there won't be any python in the finished environment
        return None

    @staticmethod
    def make_link_actions(transaction_context, package_info, target_prefix, requested_link_type):
        required_quad = transaction_context, package_info, target_prefix, requested_link_type

        file_link_actions = LinkPathAction.create_file_link_actions(*required_quad)
        create_directory_actions = LinkPathAction.create_directory_actions(
            *required_quad, file_link_actions=file_link_actions
        )
        create_nonadmin_actions = CreateNonadminAction.create_actions(*required_quad)
        create_menu_actions = MakeMenuAction.create_actions(*required_quad)

        python_entry_point_actions = CreatePythonEntryPointAction.create_actions(*required_quad)
        compile_pyc_actions = CompilePycAction.create_actions(*required_quad,
                                                              file_link_actions=file_link_actions)

        application_entry_point_actions = CreateApplicationEntryPointAction.create_actions(
            *required_quad
        )
        private_envs_meta_actions = CreatePrivateEnvMetaAction.create_actions(*required_quad)

        all_target_short_paths = tuple(axn.target_short_path for axn in concatv(
            file_link_actions,
            python_entry_point_actions,
            compile_pyc_actions,
            application_entry_point_actions,
        ))
        meta_create_actions = CreateLinkedPackageRecordAction.create_actions(
            *required_quad, all_target_short_paths=all_target_short_paths
        )
        # the ordering here is significant
        return tuple(concatv(
            meta_create_actions,
            create_directory_actions,
            file_link_actions,
            create_nonadmin_actions,
            python_entry_point_actions,
            compile_pyc_actions,
            create_menu_actions,
            application_entry_point_actions,
            private_envs_meta_actions,
        ))


def run_script(prefix, dist, action='post-link', env_prefix=None):
    """
    call the post-link (or pre-unlink) script, and return True on success,
    False on failure
    """
    path = join(prefix,
                'Scripts' if on_win else 'bin',
                '.%s-%s.%s' % (dist.name, action, 'bat' if on_win else 'sh'))
    if not isfile(path):
        return True

    env = os.environ.copy()

    if action == 'pre-link':
        is_old_noarch = False
        try:
            with open(path) as f:
                script_text = ensure_text_type(f.read())
            if ((on_win and "%PREFIX%\\python.exe %SOURCE_DIR%\\link.py" in script_text)
                    or "$PREFIX/bin/python $SOURCE_DIR/link.py" in script_text):
                is_old_noarch = True
        except Exception as e:
            import traceback
            log.debug(e)
            log.debug(traceback.format_exc())

        env['SOURCE_DIR'] = prefix
        if not is_old_noarch:
            warnings.warn(dals("""
            Package %s uses a pre-link script. Pre-link scripts are potentially dangerous.
            This is because pre-link scripts have the ability to change the package contents in the
            package cache, and therefore modify the underlying files for already-created conda
            environments.  Future versions of conda may deprecate and ignore pre-link scripts.
            """) % dist)

    if on_win:
        try:
            command_args = [os.environ[str('COMSPEC')], '/c', path]
        except KeyError:
            log.info("failed to run %s for %s due to COMSPEC KeyError", action, dist)
            return False
    else:
        shell_path = '/bin/sh' if 'bsd' in sys.platform else '/bin/bash'
        command_args = [shell_path, "-x", path]

    env['ROOT_PREFIX'] = context.root_prefix
    env['PREFIX'] = env_prefix or prefix
    env['PKG_NAME'] = dist.name
    env['PKG_VERSION'] = dist.version
    env['PKG_BUILDNUM'] = dist.build_number
    env['PATH'] = os.pathsep.join((dirname(path), env.get('PATH', '')))

    try:
        log.debug("for %s at %s, executing script: $ %s",
                  dist, env['PREFIX'], ' '.join(command_args))
        subprocess_call(command_args, env=env, path=dirname(path))
    except CalledProcessError as e:
        m = messages(prefix)
        if action in ('pre-link', 'post-link'):
            if 'openssl' in text_type(dist):
                # this is a hack for conda-build string parsing in the conda_build/build.py
                #   create_env function
                message = "%s failed for: %s" % (action, dist)
            else:
                message = dals("""
                %s script failed for package %s
                running your command again with `-v` will provide additional information
                location of failed script: %s
                ==> script messages <==
                %s
                """) % (action, dist, path, m or "<None>")
            raise LinkError(message)
        else:
            log.warn("%s script failed for package %s\n"
                     "consider notifying the package maintainer", action, dist)
            return False
    else:
        messages(prefix)
        return True


def messages(prefix):
    path = join(prefix, '.messages.txt')
    try:
        if isfile(path):
            with open(path) as fi:
                m = fi.read()
                print(m, file=sys.stderr if context.json else sys.stdout)
                return m
    finally:
        rm_rf(path)
