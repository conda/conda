# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda notices`.

Manually retrieves channel notifications, caches them and displays them.
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from .helpers import add_parser_channels, add_parser_json

    summary = "Retrieve latest channel notifications."
    description = dals(
        f"""
        {summary}

        Conda channel maintainers have the option of setting messages that
        users will see intermittently. Some of these notices are informational
        while others are messages concerning the stability of the channel.

        """
    )
    epilog = dals(
        """
        Examples:

            conda notices

            conda notices -c defaults

        """
    )

    p = sub_parsers.add_parser(
        "notices",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )
    add_parser_channels(p)
    add_parser_json(p)
    p.add_argument(
        "--plugin",
        action="store_true",
        default=False,
        help="Show only plugin-sourced notices.",
    )

    p.set_defaults(func="conda.cli.main_notices.execute")

    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    """Command that retrieves channel notifications, caches them and displays them."""
    from ..base.context import context
    from ..exceptions import CondaError
    from ..models.channel import get_channel_objs
    from ..notices import core as notices
    from ..notices.dispatch import NoticeBus

    NoticeBus.clear()
    notices.broadcast_plugin_notices()

    try:
        from ..notices import cache as notices_cache

        # Validate cache access before fetching — also triggers early
        # PermissionError / OSError when the cache dir/file can't be created
        # (e.g. unwritable filesystem), mirroring the pre-bus behaviour.
        notices_cache.get_notices_cache_file()

        if not args.plugin:
            channel_name_urls = notices.get_channel_name_and_urls(
                get_channel_objs(context),
            )
            notices.broadcast_channel_notices(
                channel_name_urls, silent=False, force=True
            )

        notices.show_notices(
            NoticeBus.consume(),
            always_show_viewed=True,
        )
        NoticeBus.commit_channel_fetch_interval()
    except OSError as exc:
        raise CondaError(f"Unable to retrieve notices: {exc}")

    return 0
