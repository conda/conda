# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from datetime import datetime

from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.models.channel import Channel
from conda.models.environment import ChannelOptions, Environment, SolverOptions
from conda.models.match_spec import MatchSpec


def test_environment():
    env = Environment(
        name="test",
        channels="conda-forge",
        requirements=["python", "numpy<2"],
        constraints=["blas"],
        last_modified="2024-01-01 00:10:00",
    )
    assert env.name == env.prefix.name == "test"
    assert env.description == ""
    assert env.requirements == [MatchSpec("python"), MatchSpec("numpy<2")]
    assert env.constraints == [MatchSpec("blas")]
    assert env.channels == [Channel("conda-forge")]
    assert env.channel_options.repodata_fns == context.repodata_fns
    assert env.solver_options.solver == context.solver
    assert env.solver_options.channel_priority == context.channel_priority
    assert env.last_modified == datetime.fromisoformat("2024-01-01 00:10:00")
    assert env.configuration == {}
    assert env.variables == {}


def test_environment_name_prefix(tmp_path):
    env = Environment(prefix=tmp_path)
    assert env.name == tmp_path.name


def test_environment_merge():
    env1 = Environment(
        name="user-provided",
        channels="conda-forge",
        requirements=["python"],
        solver_options=SolverOptions(solver="libmamba"),
        channel_options=ChannelOptions(repodata_fns="repodata.json"),
        variables={"var1": "one", "var2": "two"},
        configuration={},
        validate=False,  # disable validate to not instantiate default values
    )
    env2 = Environment(
        name="file-provided",
        description="The file description",
        requirements=["numpy<2"],
        constraints=["blas"],
        solver_options=SolverOptions(solver="libmamba"),
        variables={"var1": "uno", "var3": "three"},
        configuration={},
        validate=False,
    )
    merged = Environment.merge(env1, env2)
    assert merged.name == env1.name  # first truthy value wins
    assert merged.description == env2.description  # first truthy value wins
    assert merged.channels == env1.channels
    assert merged.requirements == env1.requirements + env2.requirements
    assert merged.constraints == env1.constraints + env2.constraints
    # All instances of SolverOptions and ChannelOptions must be equal across envs
    # otherwise an error is raised
    assert merged.solver_options == env1.solver_options == env2.solver_options
    assert merged.channel_options == env1.channel_options
    # Dicts are reduced from first to last; later appearances of the same key override
    # existing ones (see 'var1' being 'uno' and not 'one')
    assert merged.variables == {"var1": "uno", "var3": "three", "var2": "two"}
    # We might need a different merge strategy here (using the same one used for context
    # initialization across several condarc files)
    assert merged.configuration == {}


def test_environment_from_prefix(tmp_env):
    with tmp_env("ca-certificates") as prefix:
        pd = PrefixData(prefix)
        pd.set_environment_env_vars({"MYVAR": "MYVALUE"})
        (prefix / "condarc").write_text("changeps1: true")
        (prefix / "conda-meta" / "pinned").write_text("python=3.9\n")
        env = Environment.from_prefix(prefix, load_history=True)
        assert env.name == prefix.name
        assert env.prefix == prefix
        assert env.requirements == [MatchSpec("ca-certificates")]
        assert env.constraints == [MatchSpec("python=3.9", optional=True)]
        assert env.variables == {"MYVAR": "MYVALUE"}
        assert env.configuration == {"changeps1": True}
