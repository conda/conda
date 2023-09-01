# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines the offline transport adapter which is automatically used when
context.offline is True.
"""
from ....auxlib.ish import dals
from .. import BaseAdapter


class OfflineAdapter(BaseAdapter):
    def send(self, request, *args, **kwargs):
        message = dals(
            f"""
        OfflineAdapter called with url {request.url}
        This command is using a remote connection in offline mode.
        """
        )
        raise RuntimeError(message)

    def close(self):
        raise NotImplementedError()
