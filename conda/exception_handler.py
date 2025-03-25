# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Error handling and error reporting."""

import os
import sys
from functools import cached_property
from logging import getLogger

from .common.compat import ensure_text_type, on_win

log = getLogger(__name__)


class ExceptionHandler:
    def __call__(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            _, exc_val, exc_tb = sys.exc_info()
            return self.handle_exception(exc_val, exc_tb)

    def write_out(self, *content):
        from logging import getLogger

        from .cli.main import init_loggers

        init_loggers()
        getLogger("conda.stderr").info("\n".join(content))

    @property
    def http_timeout(self):
        from .base.context import context

        return context.remote_connect_timeout_secs, context.remote_read_timeout_secs

    @property
    def user_agent(self):
        from .base.context import context

        return context.user_agent

    @property
    def error_upload_url(self):
        from .base.context import context

        return context.error_upload_url

    def handle_exception(self, exc_val, exc_tb):
        from errno import ENOSPC

        from .exceptions import (
            CondaError,
            CondaMemoryError,
            NoSpaceLeftError,
        )

        if isinstance(exc_val, CondaError):
            if exc_val.reportable:
                return self.handle_reportable_application_exception(exc_val, exc_tb)
            else:
                return self.handle_application_exception(exc_val, exc_tb)
        if isinstance(exc_val, EnvironmentError):
            if getattr(exc_val, "errno", None) == ENOSPC:
                return self.handle_application_exception(
                    NoSpaceLeftError(exc_val), exc_tb
                )
        if isinstance(exc_val, MemoryError):
            return self.handle_application_exception(CondaMemoryError(exc_val), exc_tb)
        if isinstance(exc_val, KeyboardInterrupt):
            self._print_conda_exception(CondaError("KeyboardInterrupt"), exc_tb)
            return 1
        if isinstance(exc_val, SystemExit):
            return exc_val.code
        return self.handle_unexpected_exception(exc_val, exc_tb)

    def handle_application_exception(self, exc_val, exc_tb):
        self._print_conda_exception(exc_val, exc_tb)
        return exc_val.return_code

    def _print_conda_exception(self, exc_val, exc_tb):
        from .exceptions import print_conda_exception

        print_conda_exception(exc_val, exc_tb)

    def handle_unexpected_exception(self, exc_val, exc_tb):
        error_report = self.get_error_report(exc_val, exc_tb)
        self.print_unexpected_error_report(error_report)
        rc = getattr(exc_val, "return_code", None)
        return rc if rc is not None else 1

    def handle_reportable_application_exception(self, exc_val, exc_tb):
        error_report = self.get_error_report(exc_val, exc_tb)
        from .base.context import context

        if context.json:
            error_report.update(exc_val.dump_map())
        self.print_expected_error_report(error_report)
        return exc_val.return_code

    def get_error_report(self, exc_val, exc_tb):
        from .exceptions import CondaError, _format_exc

        command = " ".join(ensure_text_type(s) for s in sys.argv)
        info_dict = {}
        if " info" not in command:
            # get info_dict, but if we get an exception here too, record it without trampling
            # the original exception
            try:
                from .cli.main_info import get_info_dict

                info_dict = get_info_dict()
            except Exception as info_e:
                info_traceback = _format_exc()
                info_dict = {
                    "error": repr(info_e),
                    "exception_name": info_e.__class__.__name__,
                    "exception_type": str(exc_val.__class__),
                    "traceback": info_traceback,
                }

        error_report = {
            "error": repr(exc_val),
            "exception_name": exc_val.__class__.__name__,
            "exception_type": str(exc_val.__class__),
            "command": command,
            "traceback": _format_exc(exc_val, exc_tb),
            "conda_info": info_dict,
        }

        if isinstance(exc_val, CondaError):
            error_report["conda_error_components"] = exc_val.dump_map()

        return error_report

    def print_unexpected_error_report(self, error_report):
        from .base.context import context

        if context.json:
            from .cli.common import stdout_json

            stdout_json(error_report)
        else:
            message_builder = []
            message_builder.append("")
            message_builder.append(
                "# >>>>>>>>>>>>>>>>>>>>>> ERROR REPORT <<<<<<<<<<<<<<<<<<<<<<"
            )
            message_builder.append("")
            message_builder.extend(
                "    " + line for line in error_report["traceback"].splitlines()
            )
            message_builder.append("")
            message_builder.append("`$ {}`".format(error_report["command"]))
            message_builder.append("")
            if error_report["conda_info"]:
                from .cli.main_info import get_env_vars_str, get_main_info_str

                try:
                    # TODO: Sanitize env vars to remove secrets (e.g credentials for PROXY)
                    message_builder.append(get_env_vars_str(error_report["conda_info"]))
                    message_builder.append(
                        get_main_info_str(error_report["conda_info"])
                    )
                except Exception as e:
                    log.warning("%r", e, exc_info=True)
                    message_builder.append("conda info could not be constructed.")
                    message_builder.append(f"{e!r}")
            message_builder.extend(
                [
                    "",
                    "An unexpected error has occurred. Conda has prepared the above report."
                    "",
                    "If you suspect this error is being caused by a malfunctioning plugin,",
                    "consider using the --no-plugins option to turn off plugins.",
                    "",
                    "Example: conda --no-plugins install <package>",
                    "",
                    "Alternatively, you can set the CONDA_NO_PLUGINS environment variable on",
                    "the command line to run the command without plugins enabled.",
                    "",
                    "Example: CONDA_NO_PLUGINS=true conda install <package>",
                    "",
                ]
            )
            self.write_out(*message_builder)

    def print_expected_error_report(self, error_report):
        from .base.context import context

        if context.json:
            from .cli.common import stdout_json

            stdout_json(error_report)
        else:
            message_builder = []
            message_builder.append("")
            message_builder.append(
                "# >>>>>>>>>>>>>>>>>>>>>> ERROR REPORT <<<<<<<<<<<<<<<<<<<<<<"
            )
            message_builder.append("")
            message_builder.append("`$ {}`".format(error_report["command"]))
            message_builder.append("")
            if error_report["conda_info"]:
                from .cli.main_info import get_env_vars_str, get_main_info_str

                try:
                    # TODO: Sanitize env vars to remove secrets (e.g credentials for PROXY)
                    message_builder.append(get_env_vars_str(error_report["conda_info"]))
                    message_builder.append(
                        get_main_info_str(error_report["conda_info"])
                    )
                except Exception as e:
                    log.warning("%r", e, exc_info=True)
                    message_builder.append("conda info could not be constructed.")
                    message_builder.append(f"{e!r}")
            message_builder.append("")
            message_builder.append(
                "V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V"
            )
            message_builder.append("")

            message_builder.extend(error_report["error"].splitlines())
            message_builder.append("")

            message_builder.append(
                "A reportable application error has occurred. Conda has prepared the above report."
            )
            message_builder.append("")
            self.write_out(*message_builder)

    @cached_property
    def _isatty(self):
        try:
            return os.isatty(0) or on_win
        except Exception as e:
            log.debug("%r", e)
            return True


def conda_exception_handler(func, *args, **kwargs):
    exception_handler = ExceptionHandler()
    return_value = exception_handler(func, *args, **kwargs)
    return return_value
