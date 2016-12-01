# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.base.constants import LinkType
from conda.common.path import win_path_ok, get_python_path, pyc_path
from conda.core.linked_data import set_linked_data, delete_linked_data
from conda.exceptions import PaddingError
from conda.gateways.disk.create import create_link, make_menu, compile_pyc, write_conda_meta_record
from conda.gateways.disk.delete import rm_rf, maybe_rmdir_if_empty
from conda.gateways.disk.read import exists
from conda.gateways.disk.update import rename, update_prefix, _PaddingError
from conda.models.record import Record
from conda.utils import on_win
from logging import getLogger

log = getLogger(__name__)


class PathAction(object):

    def __init__(self, transaction_context, associated_package_info,
                 source_prefix, source_short_path,
                 target_prefix, target_short_path):
        self.transaction_context = transaction_context
        self.associated_package_info = associated_package_info
        self._source_prefix = source_prefix
        self._source_short_path = source_short_path
        self._target_prefix = target_prefix
        self._target_short_path = target_short_path

    @property
    def source_full_path(self):
        prfx, shrt_pth = self.source_prefix, self.source_short_path
        return join(prfx, win_path_ok(shrt_pth)) if prfx and shrt_pth else None

    @property
    def target_full_path(self):
        trgt, shrt_pth = self.target_prefix, self.target_short_path
        return join(trgt, win_path_ok(shrt_pth)) if trgt and shrt_pth else None

    @property
    def source_prefix(self):
        return self._source_prefix % self.transaction_context

    @property
    def source_short_path(self):
        return self._source_short_path % self.transaction_context

    @property
    def target_prefix(self):
        return self._target_prefix % self.transaction_context

    @property
    def target_short_path(self):
        return self._target_short_path % self.transaction_context

    def verify(self):
        raise NotImplementedError()

    def execute(self):
        raise NotImplementedError()

    def reverse(self):
        raise NotImplementedError()

    def cleanup(self):
        raise NotImplementedError()


class CreatePathAction(PathAction):
    # All CreatePathAction subclasses must create a SINGLE new path
    #   the short/in-prefix version of that path must be returned by execute()

    def verify(self):
        if getattr(self, 'link_type', None) == LinkType.directory:
            return
        if self.target_short_path in self.transaction_context['prefix_inventory']:
            raise VerificationError()
        self.transaction_context['prefix_inventory'].update(self.target_short_path)

    def cleanup(self):
        # create actions typically won't need cleanup
        pass


class LinkPathAction(CreatePathAction):

    def __init__(self, transaction_context, associated_package_info,
                 extracted_package_dir, source_short_path,
                 target_prefix, target_short_path, link_type):
        super(LinkPathAction, self).__init__(transaction_context, associated_package_info,
                                             extracted_package_dir, source_short_path,
                                             target_prefix, target_short_path)
        self.link_type = link_type

    def verify(self):
        super(LinkPathAction, self).verify()
        if not self.link_type == LinkType.directory and not exists(self.source_full_path):
            raise VerificationError()

    def execute(self):
        create_link(self.source_full_path, self.target_full_path, self.link_type)

    def reverse(self):
        if self.link_type == LinkType.directory:
            maybe_rmdir_if_empty(self.target_full_path)
        else:
            rm_rf(self.target_full_path)


class PrefixReplaceLinkAction(LinkPathAction):

    def __init__(self, transaction_context, associated_package_info,
                 extracted_package_dir, source_short_path,
                 target_prefix, target_short_path, prefix_placeholder, file_mode):
        super(PrefixReplaceLinkAction, self).__init__(transaction_context, associated_package_info,
                                                      extracted_package_dir, source_short_path,
                                                      target_prefix, target_short_path,
                                                      LinkType.copy)
        assert prefix_placeholder
        self.prefix_placeholder = prefix_placeholder
        self.file_mode = file_mode

    def execute(self):
        super(PrefixReplaceLinkAction, self).execute()
        try:
            update_prefix(self.target_full_path, self.target_prefix, self.prefix_placeholder,
                          self.file_mode)
        except _PaddingError:
            raise PaddingError(self.target_full_path, self.prefix_placeholder,
                               len(self.prefix_placeholder))


class MakeMenuAction(CreatePathAction):

    def __init__(self, transaction_context, associated_package_info,
                 target_prefix, target_short_path):
        super(MakeMenuAction, self).__init__(transaction_context, associated_package_info,
                                             None, None, target_prefix, target_short_path)

    def verify(self):
        pass

    def execute(self):
        make_menu(self.target_prefix, self.target_short_path, remove=False)

    def reverse(self):
        make_menu(self.target_prefix, self.target_short_path, remove=True)


class CompilePycAction(CreatePathAction):

    def __init__(self, transaction_context, associated_package_info, target_prefix,
                 source_short_path):
        super(CompilePycAction, self).__init__(transaction_context, associated_package_info,
                                               target_prefix, source_short_path,
                                               target_prefix, None)

    def execute(self):
        python_short_path = get_python_path(self.transaction_context['target_python_version'])
        python_full_path = join(self.target_prefix, win_path_ok(python_short_path))
        compile_pyc(python_full_path, self.source_full_path)

    def reverse(self):
        rm_rf(self.target_full_path)

    @property
    def target_short_path(self):
        return pyc_path(self._target_short_path, self.transaction_context['python_version'])


class CreatePythonEntryPointAction(CreatePathAction):
    # create_entry_point(entry_point, self.prefix)

    def __init__(self, transaction_context, associated_package_info,
                 target_prefix, target_short_path, module, func):
        args = (transaction_context, associated_package_info, None, None,
                target_prefix, target_short_path)
        super(CreatePythonEntryPointAction, self).__init__(*args)
        self.module = module
        self.func = func

    def execute(self):
        if on_win:
            create_windows_entry_point_py(self.target_full_path, self.module, self.func)
        else:
            python_short_path = get_python_path(self.transaction_context['target_python_version'])
            python_full_path = join(self.target_prefix, win_path_ok(python_short_path))
            create_unix_entry_point(self.target_full_path, python_full_path, self.module, self.func)

    def reverse(self):
        rm_rf(self.target_full_path)

    @property
    def target_short_path(self):
        return self._target_short_path + '-script.py' if on_win else self._target_short_path


class CreateCondaMetaAction(CreatePathAction):

    def __init__(self, transaction_context, associated_package_info, target_prefix, meta_record):
        target_short_path = 'conda-meta/' + associated_package_info.dist.to_filename('.json')
        super(CreateCondaMetaAction, self).__init__(transaction_context, associated_package_info,
                                                    None, None, target_prefix, target_short_path)
        self.meta_record = meta_record

    def execute(self):
        write_conda_meta_record(self.target_prefix, self.meta_record)
        set_linked_data(self.target_prefix, self.associated_package_info.dist.dist_name,
                        self.meta_record)

    def reverse(self):
        delete_linked_data(self.target_prefix, self.associated_package_info.dist, delete=False)
        rm_rf(self.target_full_path)


class RemovePathAction(PathAction):
    # remove actions won't have a source

    def __init__(self, transaction_context, associated_package_info,
                 target_prefix, target_short_path):
        super(RemovePathAction, self).__init__(transaction_context, associated_package_info,
                                               None, None, target_prefix, target_short_path)

    def verify(self):
        # inability to remove will trigger a rollback
        # can't definitely know if path can be removed until it's done
        pass


class UnlinkPathAction(RemovePathAction):
    def __init__(self, transaction_context, associated_package_info,
                 target_prefix, target_short_path):
        super(UnlinkPathAction, self).__init__(transaction_context, associated_package_info,
                                               target_prefix, target_short_path)
        path = join(target_prefix, target_short_path)
        self.unlink_path = path
        self.holding_path = path + '.c~'

    def verify(self):
        self.transaction_context['prefix_inventory'].pop(self.target_short_path, None)
        # technically not verification; this is mutating state of the prefix_inventory
        # however it's related to verification, because the functionality is used in other
        #   verification methods

    def execute(self):
        rename(self.unlink_path, self.holding_path)

    def reverse(self):
        rename(self.holding_path, self.unlink_path)

    def cleanup(self):
        rm_rf(self.holding_path)


class RemoveMenuAction(RemovePathAction):

    def __init__(self, transaction_context, associated_package_info,
                 target_prefix, target_short_path):
        super(RemoveMenuAction, self).__init__(transaction_context, associated_package_info,
                                               target_prefix, target_short_path)

    def execute(self):
        make_menu(self.target_prefix, self.target_short_path, remove=False)

    def reverse(self):
        make_menu(self.target_prefix, self.target_short_path, remove=True)

    def cleanup(self):
        pass


class RemoveCondaMetaAction(RemovePathAction):

    def __init__(self, transaction_context, associated_package_info,
                 target_prefix, target_short_path):
        super(RemoveCondaMetaAction, self).__init__(transaction_context, associated_package_info,
                                                    target_prefix, target_short_path)

    def execute(self):
        super(RemoveCondaMetaAction, self).execute()
        delete_linked_data(self.target_prefix, self.associated_package_info.dist, delete=False)

    def reverse(self):
        super(RemoveCondaMetaAction, self).reverse()
        with open(self.target_full_path, 'r') as fh:
            meta_record = Record(**json.loads(fh.read()))
        set_linked_data(self.target_prefix, self.associated_package_info.dist.dist_name,
                        meta_record)
