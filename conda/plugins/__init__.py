import sys

from typing import Callable, List, NamedTuple, Optional

import pluggy


if sys.version_info < (3, 9):
    from typing import Iterable
else:
    from collections.abc import Iterable


_hookspec = pluggy.HookspecMarker('conda')
hookimp = pluggy.HookimplMarker('conda')


class CondaSubcommand(NamedTuple):
    """Conda subcommand entry.

    :param name: Subcommand name (as-in ``conda my-subcommand-name``).
    :param summary: Subcommand summary, will be shown in ``conda --help``.
    :param action: Callable that will be run when the subcommand is invoked.
    """
    name: str
    summary: str
    action: Callable[
        [List[str]],  # arguments
        Optional[int],  # return code
    ]


@_hookspec
def conda_cli_register_subcommands() -> Iterable[CondaSubcommand]:
    """Register external subcommands in Conda.

    :return: An iterable of subcommand entries.
    """


class CondaVirtualPackage(NamedTuple):
    name: str
    version: Optional[str]


@_hookspec
def conda_cli_register_virtual_packages() -> Iterable[CondaVirtualPackage]:
    """Register virtual packages in Conda.

    :return: An iterable of virtual package entries.
    """
