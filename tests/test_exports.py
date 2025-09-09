# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations


# TODO: will need to be re-enabled for `CondaJSONEncoder` deprecation warning in 26.3
# @pytest.mark.parametrize(
#     "function,raises",
#     [
#         ("EntityEncoder", TypeError),
#     ],
# )
# def test_deprecations(function: str, raises: type[Exception] | None) -> None:
#     raises_context = pytest.raises(raises) if raises else nullcontext()
#     with pytest.deprecated_call(), raises_context:
#         getattr(exports, function)()
