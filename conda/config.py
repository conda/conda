# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import absolute_import, division, print_function, unicode_literals

from .base.context import context, non_x86_linux_machines, sys_rc_path, user_rc_path

non_x86_linux_machines = non_x86_linux_machines
sys_rc_path, user_rc_path = sys_rc_path, user_rc_path


# ----- rc file -----

# This is used by conda config to check which keys are allowed in the config
# file. Be sure to update it when new keys are added.

#################################################################
# Also update the example condarc file when you add a key here! #
#################################################################

root_dir = context.root_prefix
root_writable = context.root_writable

get_rc_urls = lambda: context.channels

envs_dirs = context.envs_dirs

pkgs_dirs = list(context.pkgs_dirs)
default_prefix = context.default_prefix
subdir = context.subdir
arch_name = context.arch_name
bits = context.bits
platform = context.platform

# put back because of conda build
default_python = context.default_python
binstar_upload = context.anaconda_upload
