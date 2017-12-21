# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
from os.path import dirname, exists, isfile, join, lexists
import re
from subprocess import CalledProcessError
import sys

from conda._vendor.auxlib.ish import dals

from .. import CONDA_PACKAGE_ROOT
from .._vendor.auxlib.type_coercion import boolify
from ..base.context import context
from ..common.compat import on_mac, on_win, string_types
from ..common.path import expand
from ..gateways.disk import mkdir_p
from ..gateways.disk.create import create_soft_link_or_copy
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.permissions import make_writable
from ..gateways.subprocess import subprocess_call

log = getLogger(__name__)



ALL_SHELLS = (
    'cmd_exe',
    'bash',
    'zsh',
    # 'fish',
    # 'tcsh',
)

def execute(args, parser):
    changed = False
    selected_shells = set(s for s in ALL_SHELLS if getattr(args, s, None))
    if not selected_shells:
        selected_shells.add('cmd' if on_win else 'bash')

    if not (args.user and args.system):
        args.user = True

    if selected_shells & {'bash', 'zsh'}:
        conda_sh_base_path = join(context.conda_prefix, 'etc', 'profile.d', 'conda.sh')
        changed += conda_unix_entry_point()
        changed += init_sh_base(conda_sh_base_path)
        if 'bash' in selected_shells and args.user:
            bashrc_path = expand(join('~', '.bash_profile' if on_mac else '.bashrc'))
            changed += init_sh_user(bashrc_path, conda_sh_base_path, args.auto_activate)
        if 'zsh' in selected_shells and args.user:
            changed += init_sh_user(expand(join('~', '.zshrc')), conda_sh_base_path, args.auto_activate)
        if args.system:
            changed += init_sh_system(conda_sh_base_path)
            changed += init_sh_system_activate(args.auto_activate)

    if changed:
        print("\n==> For changes to take effect, close and re-open your current shell. <==\n")
    else:
        print("No action taken.")


def conda_unix_entry_point():
    changed = False
    conda_ep_path = join(context.conda_prefix, 'bin', 'conda')

    if isfile(conda_ep_path):
        with open(conda_ep_path) as fh:
            original_ep_content = fh.read()
    else:
        original_ep_content = ""

    new_ep_content = dals("""
    #!%s
    # -*- coding: utf-8 -*-

    if __name__ == '__main__':
        import sys
        from conda.cli import main
        sys.exit(main())
    """) % '/'.join((context.conda_prefix, 'bin', 'python'))

    if new_ep_content != original_ep_content:
        mkdir_p(dirname(conda_ep_path))
        with open(conda_ep_path, 'w') as fdst:
            fdst.write(new_ep_content)
        print("%s\n  modified" % conda_ep_path)
        changed = True
    else:
        print("%s\n  no change" % conda_ep_path)

    return changed


def init_sh_base(conda_sh_base_path):
    changed = False
    conda_sh_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'profile.d', 'conda.sh')

    if isfile(conda_sh_base_path):
        with open(conda_sh_base_path) as fh:
            original_conda_sh = fh.read()
    else:
        original_conda_sh = ""

    new_conda_sh = '_CONDA_EXE="%s"\n' % join(context.conda_prefix, 'bin', 'conda')
    new_conda_sh += '_CONDA_ROOT="%s"\n' % context.conda_prefix
    with open(conda_sh_src_path) as fsrc:
        new_conda_sh += fsrc.read()

    if new_conda_sh != original_conda_sh:
        mkdir_p(dirname(conda_sh_base_path))
        with open(conda_sh_base_path, 'w') as fdst:
            fdst.write(new_conda_sh)
        print("%s\n  modified" % conda_sh_base_path)
        changed = True
    else:
        print("%s\n  no change" % conda_sh_base_path)

    return changed


def init_sh_user(user_rc_path, conda_sh_base_path, auto_activate):
    changed = False
    with open(user_rc_path) as fh:
        bashrc_content = fh.read()

    bashrc_original_content = bashrc_content

    if auto_activate:
        conda_initialize_content = (
            '# >>> conda initialize >>>\n'
            '. "%s"\n'
            'conda activate base\n'
            '# <<< conda initialize <<<'
        ) % conda_sh_base_path
    else:
        conda_initialize_content = (
            '# >>> conda initialize >>>\n'
            '. "%s"\n'
            '# <<< conda initialize <<<'
        ) % conda_sh_base_path

    bashrc_content = re.sub(
        r"^[ \t]*(export PATH=['\"]%s:\$PATH['\"])[ \t]*$" % re.escape(join(context.conda_prefix, 'bin')),
        r"# \1  # modified by conda initialize",
        bashrc_content,
        flags=re.MULTILINE,
    )
    bashrc_content = re.sub(
        r"^[ \t]*[^#\n]?[ \t]*((?:source|\.) .*\/etc\/profile\.d\/conda\.sh)[ \t]*$",
        r"# \1  # modified by conda initialize",
        bashrc_content,
        flags=re.MULTILINE,
    )
    bashrc_content = re.sub(
        r"^# >>> conda initialize >>>$([\s\S]*?)# <<< conda initialize <<<$",
        conda_initialize_content,
        bashrc_content,
        flags=re.MULTILINE,
    )

    if "# >>> conda initialize >>>" not in bashrc_content:
        bashrc_content += '\n%s\n' % conda_initialize_content

    if bashrc_content != bashrc_original_content:
        with open(user_rc_path, 'w') as fh:
            fh.write(bashrc_content)
        print("%s\n  modified" % user_rc_path)
        changed = True
    else:
        print("%s\n  no change" % user_rc_path)

    return changed


def init_sh_system(conda_sh_base_path):
    changed = False
    conda_sh_system_path = '/etc/profile.d/conda.sh'
    if exists(conda_sh_system_path):
        with open(conda_sh_system_path) as fh:
            conda_sh_system_contents = fh.read()
    else:
        conda_sh_system_contents = ""
    with open(conda_sh_base_path) as fh:
        conda_sh_contents = fh.read()
    if conda_sh_system_contents != conda_sh_contents:
        try:
            if lexists(conda_sh_system_path):
                rm_rf(conda_sh_system_path)
            mkdir_p(dirname(conda_sh_system_path))
            create_soft_link_or_copy(conda_sh_base_path, conda_sh_system_path)
            print("%s\n  modified" % conda_sh_system_path)
            changed = True
        except (IOError, OSError) as e:
            log.debug("%r", e, exc_info=True)
            print("The current user cannot modify the path %s" % conda_sh_system_path)
            print("Conda will retry, requesting elevated privileges. You may be asked to enter your password.")
            try:
                resp = subprocess_call(
                    'sudo %s -m conda.cli.main_initialize init_sh_system "%s"' % (sys.executable, conda_sh_base_path),
                    cwd=os.getcwd(),
                )
                if resp.rc == 0:
                    if resp.stdout:
                        print(resp.stdout.rstrip())
                        if "modified" in resp.stdout:
                            print("%s\n  modified" % conda_sh_system_path)
                            changed = True
                    if resp.stderr:
                        print(resp.stderr.rstrip(), file=sys.stderr)
            except CalledProcessError as e:
                log.debug("%r", e, exc_info=True)
                print("An error occurred accessing path %s" % conda_sh_system_path)
                print(e.output)
    else:
        print("%s\n  no change" % conda_sh_system_path)

    return changed


def init_sh_system_activate(auto_activate):
    if isinstance(auto_activate, string_types):
        auto_activate = boolify(auto_activate)
    changed = False
    conda_activate_sh_path = '/etc/profile.d/conda_activate_base.sh'
    if auto_activate:
        if exists(conda_activate_sh_path):
            with open(conda_activate_sh_path) as fh:
                conda_activate_sh_contents = fh.read()
        else:
            conda_activate_sh_contents = ""
        conda_activate_sh_final_contents = 'conda activate base\n'

        if conda_activate_sh_final_contents != conda_activate_sh_contents:
            try:
                with open(conda_activate_sh_path, 'w') as fh:
                    fh.write(conda_activate_sh_final_contents)
                    print("%s\n  modified" % conda_activate_sh_path)
                    changed = True

            except (IOError, OSError) as e:
                log.debug("%r", e, exc_info=True)
                print("The current user cannot modify the path %s" % conda_activate_sh_path)
                print("Conda will retry, requesting elevated privileges. You may be asked to enter your password.")
                try:
                    resp = subprocess_call(
                        "sudo %s -m conda.cli.main_initialize init_sh_system_activate %s" % (sys.executable, auto_activate),
                        cwd=os.getcwd(),
                    )
                    if resp.rc == 0:
                        if resp.stdout:
                            print(resp.stdout.rstrip())
                            if "modified" in resp.stdout:
                                changed = True
                        if resp.stderr:
                            print(resp.stderr.rstrip(), file=sys.stderr)
                except CalledProcessError as e:
                    log.debug("%r", e, exc_info=True)
                    print("An error occurred accessing path %s" % conda_activate_sh_path)
                    print(e.output)
        else:
            print("%s\n  no change" % conda_activate_sh_path)

    else:
        if lexists(conda_activate_sh_path):
            try:
                make_writable(conda_activate_sh_path)
                os.unlink(conda_activate_sh_path)
                print("%s\n  modified" % conda_activate_sh_path)
                changed = True
            except (IOError, OSError) as e:
                log.debug("%r", e, exc_info=True)
                print("The current user cannot modify the path %s" % conda_activate_sh_path)
                print("Conda will retry, requesting elevated privileges. You may be asked to enter your password.")
                try:
                    resp = subprocess_call(
                        "sudo %s -m conda.cli.main_initialize init_sh_system_activate %s" % (
                        sys.executable, auto_activate),
                        cwd=os.getcwd(),
                    )
                    if resp.rc == 0:
                        if resp.stdout:
                            print(resp.stdout.rstrip())
                            if "modified" in resp.stdout:
                                changed = True
                        if resp.stderr:
                            print(resp.stderr.rstrip(), file=sys.stderr)
                except CalledProcessError as e:
                    log.debug("%r", e, exc_info=True)
                    print("An error occurred accessing path %s" % conda_activate_sh_path)
                    print(e.output)
        else:
            print("%s\n  no change" % conda_activate_sh_path)

    return changed


def init_cmd_exe():
    conda_bat_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'Library', 'bin', 'conda.bat')
    conda_bat_dst_path = join(sys.prefix, 'Library', 'bin', 'conda.bat')

    mkdir_p(dirname(conda_bat_dst_path))
    with open(conda_bat_dst_path, 'w') as fdst:
        fdst.write('@SET "_CONDA_EXE=%s"\n' % join(sys.prefix, 'Scripts', 'conda.exe'))
        with open(conda_bat_src_path) as fsrc:
            fdst.write(fsrc.read())

    # TODO: use menuinst to create shortcuts


if __name__ == "__main__":
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 1 else ()
    locals()[command](*args)
