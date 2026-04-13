# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""py-rattler implementation of create/install for conda-ng."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import (
    AwaitingConfirmation,
    SolutionPlanReady,
    SolveFinished,
    SolveStarted,
    TransactionFinished,
    TransactionStarted,
    merge_specs_for_solve,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from rattler import (
        Channel,
        GenericVirtualPackage,
        MatchSpec,
        PackageRecord,
        VirtualPackage,
    )

    from .invocation import InstallLikeInvocation
    from .types import (
        CreateRequest,
        InstallRequest,
        ProgressCallback,
        ProgressEvent,
    )


def _emit(callback: ProgressCallback | None, event: ProgressEvent) -> None:
    from .progress_reporter import progress_to_reporter

    progress_to_reporter(event)
    if callback is not None:
        callback(event)


class RattlerRunner:
    """Solve and link using py-rattler (current conda-ng engine)."""

    def create(self, request: CreateRequest) -> Iterable[PackageRecord]:
        specs = tuple(request.specs)
        return self.run_transaction(
            specs=specs,
            channels=request.channels,
            platform=request.platform,
            target_prefix=request.target_prefix,
            history=(),
            user_specs=specs,
            locked_packages=None,
            pinned_packages=request.pinned_packages,
            virtual_packages=request.virtual_packages,
            constraints=request.constraints,
            dry_run=request.dry_run,
            report=request.report,
            removing=False,
            on_progress=request.on_progress,
        )

    def install(self, request: InstallRequest) -> Iterable[PackageRecord]:
        specs = tuple(request.specs)
        history = tuple(request.history)
        return self.run_transaction(
            specs=specs,
            channels=request.channels,
            platform=request.platform,
            target_prefix=request.target_prefix,
            history=history,
            user_specs=specs,
            locked_packages=request.locked_packages,
            pinned_packages=request.pinned_packages,
            virtual_packages=request.virtual_packages,
            constraints=request.constraints,
            dry_run=request.dry_run,
            report=request.report,
            removing=False,
            on_progress=request.on_progress,
        )

    def create_cli(self, invocation: InstallLikeInvocation) -> Iterable[PackageRecord]:
        from rattler import MatchSpec

        from conda.base.context import context

        from ..cli.common import as_virtual_package

        specs = [MatchSpec(s) for s in invocation.spec_strings]
        virtual_packages = [
            as_virtual_package(pkg)
            for pkg in context.plugin_manager.get_virtual_package_records()
        ]
        return self.run_transaction(
            specs=specs,
            channels=context.channels,
            platform=context.subdir,
            target_prefix=invocation.target_prefix,
            history=(),
            user_specs=specs,
            locked_packages=None,
            pinned_packages=None,
            virtual_packages=virtual_packages,
            constraints=None,
            dry_run=context.dry_run,
            report=not context.quiet and not context.json,
            removing=False,
            on_progress=None,
        )

    def install_cli(self, invocation: InstallLikeInvocation) -> Iterable[PackageRecord]:
        from rattler import MatchSpec

        from conda.base.context import context
        from conda.history import History

        from ..cli.common import as_virtual_package, installed_packages

        prefix = str(invocation.target_prefix)
        history = [
            MatchSpec(str(spec))
            for spec in History(prefix).get_requested_specs_map().values()
        ]
        specs = [MatchSpec(s) for s in invocation.spec_strings]
        virtual_packages = [
            as_virtual_package(pkg)
            for pkg in context.plugin_manager.get_virtual_package_records()
        ]
        return self.run_transaction(
            specs=specs,
            channels=context.channels,
            platform=context.subdir,
            target_prefix=prefix,
            history=history,
            user_specs=specs,
            locked_packages=installed_packages(prefix),
            pinned_packages=None,
            virtual_packages=virtual_packages,
            constraints=None,
            dry_run=context.dry_run,
            report=not context.quiet and not context.json,
            removing=False,
            on_progress=None,
        )

    def run_transaction(
        self,
        *,
        specs: Iterable[str | MatchSpec],
        channels: Iterable[str | Channel],
        platform: str,
        target_prefix: str | Path | None = None,
        history: Iterable[str | MatchSpec] = (),
        user_specs: Iterable[str | MatchSpec] = (),
        locked_packages: Iterable[PackageRecord] | None = None,
        pinned_packages: Iterable[PackageRecord] | None = None,
        virtual_packages: Iterable[GenericVirtualPackage | VirtualPackage]
        | None = None,
        constraints: Iterable[MatchSpec] | None = None,
        dry_run: bool = False,
        report: bool = True,
        removing: bool = False,
        t0: float | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> Iterable[PackageRecord]:
        import asyncio
        import time
        import uuid

        from rattler import Client, Gateway, MatchSpec, SourceConfig, solve
        from rattler import install as rattler_install
        from rattler.exceptions import GatewayError, SolverError

        from conda.base.context import context
        from conda.exceptions import CondaError, CondaExitZero, DryRunExit
        from conda.history import History
        from conda.plugins.types import (
            SolveLifecycleBegin,
            SolveLifecycleEndFailure,
            SolveLifecycleEndSuccess,
        )
        from conda.reporters import (
            confirm_yn,
            emit_install_like_progress,
            get_solve_activity_context,
        )

        from ..cli.common import cache_dir, installed_packages
        from ..cli.planning import (
            diff_for_unlink_link_precs,
            solution_install_plan_rows,
            user_agent,
        )
        from ..exceptions import CondaSolverError

        specs = [MatchSpec(spec) if isinstance(spec, str) else spec for spec in specs]
        history = [
            MatchSpec(spec) if isinstance(spec, str) else spec for spec in history
        ]
        aggregated_specs_list = merge_specs_for_solve(history, specs)
        aggregated_specs = {s.name.normalized: s for s in aggregated_specs_list}

        client = Client(headers={"User-Agent": user_agent()})
        gateway_config = SourceConfig(
            cache_action="force-cache-only" if context.offline else "cache-or-fetch"
        )
        gateway = Gateway(
            cache_dir=cache_dir("index"),
            client=client,
            show_progress=report,
            default_config=gateway_config,
        )

        async def inner_solve():
            return await solve(
                channels,
                specs=aggregated_specs.values(),
                gateway=gateway,
                platforms=[platform, "noarch"],
                locked_packages=locked_packages,
                pinned_packages=pinned_packages,
                virtual_packages=virtual_packages,
                constraints=constraints,
            )

        if context.verbose:
            hints = [
                ("channels", ",".join(map(str, channels))),
                ("platform", platform),
            ]
            if target_prefix:
                hints.append(("prefix", str(target_prefix)))
            emit_install_like_progress({"kind": "verbose_hints", "hints": hints})

        context.plugin_manager.invoke_pre_solves(
            specs_to_add=user_specs or specs if not removing else (),
            specs_to_remove=user_specs or specs if removing else (),
        )

        span_id = str(uuid.uuid4())
        pfx = str(target_prefix) if target_prefix else ""
        n_add = len(tuple(user_specs or specs if not removing else ()))
        n_rem = len(tuple(user_specs or specs if removing else ()))
        context.plugin_manager.invoke_solve_lifecycle(
            SolveLifecycleBegin(
                span_id=span_id,
                prefix=pfx,
                solver="rattler",
                repodata_fn="repodata.json",
                command=None,
                specs_to_add_count=n_add,
                specs_to_remove_count=n_rem,
            )
        )

        if on_progress is not None:
            on_progress(SolveStarted())
        with get_solve_activity_context("Solving environment"):
            t_ls = time.perf_counter()
            try:
                records = asyncio.run(inner_solve())
            except SolverError as exc:
                dt_ls = time.perf_counter() - t_ls
                context.plugin_manager.invoke_solve_lifecycle(
                    SolveLifecycleEndFailure(
                        span_id=span_id,
                        prefix=pfx,
                        solver="rattler",
                        repodata_fn="repodata.json",
                        command=None,
                        duration_s=int(dt_ls),
                        duration_ms=(dt_ls - int(dt_ls)) * 1000,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:500],
                    )
                )
                raise CondaSolverError(str(exc)) from exc
            except GatewayError as exc:
                dt_ls = time.perf_counter() - t_ls
                context.plugin_manager.invoke_solve_lifecycle(
                    SolveLifecycleEndFailure(
                        span_id=span_id,
                        prefix=pfx,
                        solver="rattler",
                        repodata_fn="repodata.json",
                        command=None,
                        duration_s=int(dt_ls),
                        duration_ms=(dt_ls - int(dt_ls)) * 1000,
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:500],
                    )
                )
                raise CondaError(f"Connection error:\n\n{exc}") from exc
        t1 = time.perf_counter()
        dt_ls = t1 - t_ls
        dur_s_ls = int(dt_ls)
        dur_ms_ls = (dt_ls - dur_s_ls) * 1000
        if on_progress is not None:
            on_progress(
                SolveFinished(
                    record_count=len(records),
                    duration_seconds=dur_s_ls,
                    duration_ms=dur_ms_ls,
                )
            )

        if target_prefix:
            installed = list(installed_packages(target_prefix))
            if set(record.sha256 for record in installed) == set(
                record.sha256 for record in records
            ):
                context.plugin_manager.invoke_solve_lifecycle(
                    SolveLifecycleEndSuccess(
                        span_id=span_id,
                        prefix=pfx,
                        solver="rattler",
                        repodata_fn="repodata.json",
                        command=None,
                        duration_s=dur_s_ls,
                        duration_ms=dur_ms_ls,
                        unlink_count=0,
                        link_count=0,
                        record_count=len(records),
                    )
                )
                raise CondaExitZero("Nothing to do.")
        else:
            installed = ()

        to_unlink, to_link = diff_for_unlink_link_precs(
            previous_records=installed,
            new_records=records,
            specs_to_add=user_specs,
        )
        context.plugin_manager.invoke_solve_lifecycle(
            SolveLifecycleEndSuccess(
                span_id=span_id,
                prefix=pfx,
                solver="rattler",
                repodata_fn="repodata.json",
                command=None,
                duration_s=dur_s_ls,
                duration_ms=dur_ms_ls,
                unlink_count=len(to_unlink),
                link_count=len(to_link),
                record_count=len(records),
            )
        )
        context.plugin_manager.invoke_post_solves("repodata.json", to_unlink, to_link)

        if not installed and not records:
            raise CondaExitZero("Nothing to do.")

        _emit(
            on_progress,
            SolutionPlanReady(
                records=tuple(records),
                specs=tuple(specs),
                history=tuple(history),
                installed=tuple(installed),
                removing=removing,
            ),
        )

        if report:
            plan_rows, plan_caption = solution_install_plan_rows(
                records=records,
                specs=specs,
                installed=installed,
                history=history,
                removing=removing,
            )
            emit_install_like_progress(
                {
                    "kind": "install_plan_table",
                    "rows": plan_rows,
                    "caption": plan_caption,
                    "prefix": str(target_prefix) if target_prefix else "",
                    "specs_to_remove": (
                        [str(s) for s in (user_specs or specs)] if removing else []
                    ),
                    "specs_to_add": (
                        [str(s) for s in (user_specs or specs)] if not removing else []
                    ),
                }
            )

        if dry_run:
            raise DryRunExit()

        _emit(on_progress, AwaitingConfirmation(prefix=target_prefix))
        confirm_yn(f"\nApply changes to '{target_prefix}'?")

        async def inner_install():
            await rattler_install(
                records=records,
                target_prefix=target_prefix,
                installed_packages=installed or list(installed_packages(target_prefix)),
                cache_dir=cache_dir("pkgs"),
                execute_link_scripts=True,
                requested_specs=[s._match_spec for s in (user_specs or specs)],
                show_progress=report,
                client=client,
            )

        txn_context = {}
        for action in context.plugin_manager.get_pre_transaction_actions(
            transaction_context=txn_context,
            target_prefix=target_prefix,
            unlink_precs=to_unlink,
            link_precs=to_link,
            remove_specs=user_specs or specs if removing else (),
            update_specs=user_specs or specs if not removing else (),
            neutered_specs=(),
        ):
            action.execute()

        _emit(on_progress, TransactionStarted())
        with History(target_prefix) as h:
            if report:
                with get_solve_activity_context("Executing transaction"):
                    asyncio.run(inner_install())
            else:
                asyncio.run(inner_install())
        if not removing:
            h.write_specs(update_specs=list(map(str, (user_specs or specs))))
        _emit(on_progress, TransactionFinished())

        for action in context.plugin_manager.get_pre_transaction_actions(
            transaction_context=txn_context,
            target_prefix=target_prefix,
            unlink_precs=to_unlink,
            link_precs=to_link,
            remove_specs=user_specs or specs if removing else (),
            update_specs=user_specs or specs if not removing else (),
            neutered_specs=(),
        ):
            action.execute()

        return records


def default_rattler_runner() -> RattlerRunner:
    return RattlerRunner()
