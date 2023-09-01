# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from .. import BaseAdapter
from ....auxlib.ish import dals


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
