# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the built-in post_solves hook implementations.

Note: The signature_verification post-solve hook has been moved to conda-content-trust
as of conda 26.3. If you have conda-content-trust installed, the signature verification
will be provided by that plugin.
"""

plugins = []
"""The list of post-solve plugins for easier registration with pluggy."""
