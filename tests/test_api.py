# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

try:
    from inspect import getfullargspec as getargspec
except ImportError:
    from inspect import getargspec

import pytest

from conda.api import DepsModifier, PackageCacheData, PrefixData, Solver, SubdirData, \
    UpdateModifier
from conda.base.context import context
from conda.common.compat import isiterable, odict
from conda.common.constants import NULL
from conda.core.link import UnlinkLinkTransaction
from conda.models.channel import Channel
from conda.models.records import PackageCacheRecord, PackageRecord, PrefixRecord


class PositionalArgument:
    pass


def inspect_arguments(f, arguments):
    # FullArgSpec(args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations)
    result = getargspec(f)
    arg_names = result[0]
    defaults = result[3] or ()
    default_val_first_idx = len(arg_names) - len(defaults)
    arg_values = [PositionalArgument] * default_val_first_idx + list(defaults)
    for (recorded_name, recorded_value), (arg_name, arg_value) in zip(arguments.items(), zip(arg_names, arg_values)):
        print(recorded_name, arg_name)
        assert recorded_name == arg_name
        assert recorded_value == arg_value


def test_DepsModifier_contract():
    assert DepsModifier.NO_DEPS
    assert DepsModifier.ONLY_DEPS
    assert DepsModifier.NOT_SET


def test_UpdateModifier_contract():
    assert UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE
    assert UpdateModifier.FREEZE_INSTALLED
    assert UpdateModifier.UPDATE_DEPS
    assert UpdateModifier.UPDATE_SPECS
    assert UpdateModifier.UPDATE_ALL


def test_Solver_inputs_contract():
    init_args = odict((
        ('self', PositionalArgument),
        ('prefix', PositionalArgument),
        ('channels', PositionalArgument),
        ('subdirs', ()),
        ('specs_to_add', ()),
        ('specs_to_remove', ()),
    ))
    inspect_arguments(Solver.__init__, init_args)

    solve_final_state_args = odict((
        ('self', PositionalArgument),
        ('update_modifier', NULL),
        ('deps_modifier', NULL),
        ('prune', NULL),
        ('ignore_pinned', NULL),
        ('force_remove', NULL),
    ))
    inspect_arguments(Solver.solve_final_state, solve_final_state_args)

    solve_for_diff_args = odict((
        ('self', PositionalArgument),
        ('update_modifier', NULL),
        ('deps_modifier', NULL),
        ('prune', NULL),
        ('ignore_pinned', NULL),
        ('force_remove', NULL),
        ('force_reinstall', False),
    ))
    inspect_arguments(Solver.solve_for_diff, solve_for_diff_args)

    solve_for_transaction_args = odict((
        ('self', PositionalArgument),
        ('update_modifier', NULL),
        ('deps_modifier', NULL),
        ('prune', NULL),
        ('ignore_pinned', NULL),
        ('force_remove', NULL),
        ('force_reinstall', False),
    ))
    inspect_arguments(Solver.solve_for_transaction, solve_for_transaction_args)


@pytest.mark.integration
def test_Solver_return_value_contract():
    solver = Solver('/', (Channel('pkgs/main'),), specs_to_add=('openssl',))
    solve_final_state_rv = solver.solve_final_state()
    assert isiterable(solve_final_state_rv)
    assert all(isinstance(pref, PackageRecord) for pref in solve_final_state_rv)

    solve_for_diff_rv = solver.solve_for_diff()
    assert len(solve_for_diff_rv) == 2
    unlink_precs, link_precs = solve_for_diff_rv
    assert isiterable(unlink_precs)
    assert all(isinstance(pref, PackageRecord) for pref in unlink_precs)
    assert isiterable(link_precs)
    assert all(isinstance(pref, PackageRecord) for pref in link_precs)

    solve_for_transaction_rv = solver.solve_for_transaction()
    assert isinstance(solve_for_transaction_rv, UnlinkLinkTransaction)


def test_SubdirData_contract():
    init_args = odict((
        ('self', PositionalArgument),
        ('channel', PositionalArgument),
    ))
    inspect_arguments(SubdirData.__init__, init_args)

    query_args = odict((
        ('self', PositionalArgument),
        ('package_ref_or_match_spec', PositionalArgument),
    ))
    inspect_arguments(SubdirData.query, query_args)

    query_all_args = odict((
        ('package_ref_or_match_spec', PositionalArgument),
        ('channels', None),
        ('subdirs', None),
    ))
    inspect_arguments(SubdirData.query_all, query_all_args)

    iter_records_args = odict((
        ('self', PositionalArgument),
    ))
    inspect_arguments(SubdirData.iter_records, iter_records_args)

    reload_args = odict((
        ('self', PositionalArgument),
    ))
    inspect_arguments(SubdirData.reload, reload_args)


@pytest.mark.integration
def test_SubdirData_return_value_contract():
    sd = SubdirData(Channel('pkgs/main/linux-64'))
    query_result = sd.query('openssl')
    assert isinstance(query_result, tuple)
    assert all(isinstance(prec, PackageRecord) for prec in query_result)

    query_all_result = sd.query_all('openssl', (Channel('pkgs/main'),), context.subdirs)
    assert isinstance(query_all_result, tuple)
    assert all(isinstance(prec, PackageRecord) for prec in query_all_result)

    iter_records_result = sd.iter_records()
    assert isiterable(iter_records_result)
    assert all(isinstance(prec, PackageRecord) for prec in iter_records_result)

    reload_result = sd.reload()
    assert isinstance(reload_result, SubdirData)


def test_PackageCacheData_contract():
    init_args = odict((
        ('self', PositionalArgument),
        ('pkgs_dir', PositionalArgument),
    ))
    inspect_arguments(PackageCacheData.__init__, init_args)

    get_args = odict((
        ('self', PositionalArgument),
        ('package_ref', PositionalArgument),
        ('default', NULL),
    ))
    inspect_arguments(PackageCacheData.get, get_args)

    query_args = odict((
        ('self', PositionalArgument),
        ('package_ref_or_match_spec', PositionalArgument),
    ))
    inspect_arguments(PackageCacheData.query, query_args)

    query_all_args = odict((
        ('package_ref_or_match_spec', PositionalArgument),
        ('pkgs_dirs', None),
    ))
    inspect_arguments(PackageCacheData.query_all, query_all_args)

    iter_records_args = odict((
        ('self', PositionalArgument),
    ))
    inspect_arguments(PackageCacheData.iter_records, iter_records_args)

    isinstance(PackageCacheData.is_writable, property)

    first_writable_args = odict((
        ('pkgs_dirs', None),
    ))
    inspect_arguments(PackageCacheData.first_writable, first_writable_args)

    reload_args = odict((
        ('self', PositionalArgument),
    ))
    inspect_arguments(PackageCacheData.reload, reload_args)


def test_PackageCacheData_return_value_contract():
    pc = PackageCacheData(context.pkgs_dirs[0])

    single_pcrec = next(pc.iter_records(), None)
    if single_pcrec:
        get_result = pc.get(PackageRecord.from_objects(single_pcrec))
        assert isinstance(get_result, PackageCacheRecord)

    query_result = pc.query('openssl')
    assert isinstance(query_result, tuple)
    assert all(isinstance(pcrec, PackageCacheRecord) for pcrec in query_result)

    query_all_result = PackageCacheData.query_all('openssl')
    assert isinstance(query_all_result, tuple)
    assert all(isinstance(pcrec, PackageCacheRecord) for pcrec in query_all_result)

    iter_records_result = pc.iter_records()
    assert isiterable(iter_records_result)
    assert all(isinstance(pcrec, PackageCacheRecord) for pcrec in iter_records_result)

    is_writable_result = pc.is_writable
    assert is_writable_result is True or is_writable_result is False

    first_writable_result = PackageCacheData.first_writable()
    assert isinstance(first_writable_result, PackageCacheData)

    reload_result = pc.reload()
    assert isinstance(reload_result, PackageCacheData)


def test_PrefixData_contract():
    init_args = odict((
        ('self', PositionalArgument),
        ('prefix_path', PositionalArgument),
    ))
    inspect_arguments(PrefixData.__init__, init_args)

    get_args = odict((
        ('self', PositionalArgument),
        ('package_ref', PositionalArgument),
        ('default', NULL),
    ))
    inspect_arguments(PrefixData.get, get_args)

    query_args = odict((
        ('self', PositionalArgument),
        ('package_ref_or_match_spec', PositionalArgument),
    ))
    inspect_arguments(PrefixData.query, query_args)

    iter_records_args = odict((
        ('self', PositionalArgument),
    ))
    inspect_arguments(PrefixData.iter_records, iter_records_args)

    isinstance(PrefixData.is_writable, property)

    reload_args = odict((
        ('self', PositionalArgument),
    ))
    inspect_arguments(PrefixData.reload, reload_args)


def test_PrefixData_return_value_contract():
    pd = PrefixData(context.conda_prefix)

    single_prefix_rec = next(pd.iter_records())
    get_result = pd.get(PackageRecord.from_objects(single_prefix_rec))
    assert isinstance(get_result, PrefixRecord)

    query_result = pd.query('openssl')
    assert isinstance(query_result, tuple)
    assert all(isinstance(prefix_rec, PrefixRecord) for prefix_rec in query_result)

    iter_records_result = pd.iter_records()
    assert isiterable(iter_records_result)
    assert all(isinstance(prefix_rec, PrefixRecord) for prefix_rec in iter_records_result)

    is_writable_result = pd.is_writable
    assert is_writable_result is True or is_writable_result is False

    reload_result = pd.reload()
    assert isinstance(reload_result, PrefixData)
