# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
import json
from logging import getLogger
import os
from os.path import dirname, exists, isfile, join
import re
import sys

from . import CONDA_PACKAGE_ROOT
from ._vendor.auxlib.ish import dals
from ._vendor.auxlib.type_coercion import boolify
from .base.context import context
from .common.compat import on_mac, on_win, string_types
from .common.path import expand
from .gateways.disk.create import create_hard_link_or_copy, create_soft_link_or_copy, mkdir_p
from .gateways.disk.delete import rm_rf
from .gateways.disk.link import lexists
from .gateways.disk.permissions import make_executable, make_writable
from .gateways.disk.read import compute_md5sum
from .gateways.subprocess import subprocess_call

log = getLogger(__name__)

ALL_SHELLS = (
    'cmd_exe',
    'bash',
    'zsh',
    # 'fish',
    # 'tcsh',
)


class Result:
    NEEDS_SUDO = "needs sudo"
    MODIFIED = "modified"
    NO_CHANGE = "no change"


def install(conda_prefix):
    plan = make_install_plan(conda_prefix)
    run_plan(plan)
    print_plan_results(plan)


def initialize(conda_prefix, auto_activate, shells, for_user, for_system):
    plan = make_initialize_plan(conda_prefix, auto_activate, shells, for_user, for_system)
    run_plan(plan)
    run_plan_elevated(plan)
    print_plan_results(plan)


def initialize_dev():
    # > eval `$(which python) -m conda initialize --dev`

    from distutils.sysconfig import get_python_lib
    site_packages_dir = get_python_lib()

    if not isfile('conda/__init__.py'):
        print("Current working directory needs to be conda source root.", file=sys.stderr)
        return 1

    remove_conda_sp_dir(site_packages_dir)

    plan = []
    plan.append({
        'function': make_conda_pth.__name__,
        'kwargs': {
            'target_path': join(site_packages_dir, 'conda.pth'),
            'conda_source_dir': os.getcwd(),
        },
    })

    run_plan(plan)
    # print_plan_results(plan, stream=sys.stderr)
    print(". conda/shell/etc/profile.d/conda.sh")
    print("conda activate %s" % sys.prefix)


def make_install_plan(conda_prefix):
    from distutils.sysconfig import get_python_lib
    site_packages_dir = get_python_lib()

    plan = []
    _add_executables(plan, conda_prefix)
    if on_win:
        plan.append({
            'function': init_conda_bat.__name__,
            'kwargs': {
                'target_path': join(sys.prefix, 'Library', 'bin', 'conda.bat'),
            },
        })
    plan.append({
        'function': init_conda_sh.__name__,
        'kwargs': {
            'target_path': join(conda_prefix, 'etc', 'profile.d', 'conda.sh'),
            'conda_prefix': conda_prefix,
        },
    })
    plan.append({
        'function': init_conda_fish.__name__,
        'kwargs': {
            'target_path': join(conda_prefix, 'etc', 'fish', 'conf.d', 'conda.fish'),
            'conda_prefix': conda_prefix,
        },
    })
    plan.append({
        'function': init_conda_xsh.__name__,
        'kwargs': {
            'target_path': join(site_packages_dir, 'xonsh', 'conda.xsh'),
            'conda_prefix': conda_prefix,
        },
    })
    plan.append({
        'function': init_conda_csh.__name__,
        'kwargs': {
            'target_path': join(conda_prefix, 'etc', 'profile.d', 'conda.csh'),
            'conda_prefix': conda_prefix,
        },
    })
    return plan


def make_initialize_plan(conda_prefix, auto_activate, shells, for_user, for_system):
    plan = []
    _add_executables(plan, conda_prefix)

    if 'cmd_exe' in shells:
        plan.append({
            'function': init_conda_bat.__name__,
            'kwargs': {
                'target_path': join(sys.prefix, 'Library', 'bin', 'conda.bat'),
            },
        })

    if shells & {'bash', 'zsh'}:
        plan.append({
            'function': init_conda_sh.__name__,
            'kwargs': {
                'target_path': join(conda_prefix, 'etc', 'profile.d', 'conda.sh'),
                'conda_prefix': conda_prefix,
            },
        })

        if 'bash' in shells and for_user:
            bashrc_path = expand(join('~', '.bash_profile' if on_mac else '.bashrc'))
            plan.append({
                'function': init_sh_user.__name__,
                'kwargs': {
                    'target_path': bashrc_path,
                    'conda_prefix': conda_prefix,
                    'auto_activate': auto_activate,
                },
            })

        if 'zsh' in shells and for_user:
            zshrc_path = expand(join('~', '.zshrc'))
            plan.append({
                'function': init_sh_user.__name__,
                'kwargs': {
                    'target_path': zshrc_path,
                    'conda_prefix': conda_prefix,
                    'auto_activate': auto_activate,
                },
            })

        if for_system:
            plan.append({
                'function': init_sh_system.__name__,
                'kwargs': {
                    'target_path': '/etc/profile.d/conda.sh',
                    'conda_prefix': conda_prefix,
                },
            })
            plan.append({
                'function': init_sh_system_activate.__name__,
                'kwargs': {
                    'target_path': '/etc/profile.d/conda_activate_base.sh',
                    'auto_activate': auto_activate,
                },
            })

    return plan


def _add_executables(plan, conda_prefix):
    if on_win:
        conda_exe_path = join(conda_prefix, 'Scripts', 'conda-script.py')
        plan.append({
            'function': make_entry_point_exe.__name__,
            'kwargs': {
                'target_path': join(conda_prefix, 'Scripts', 'conda.exe'),
            },
        })
        conda_env_exe_path = join(conda_prefix, 'Scripts', 'conda-env-script.py')
        plan.append({
            'function': make_entry_point_exe.__name__,
            'kwargs': {
                'target_path': join(conda_prefix, 'Scripts', 'conda-env.exe'),
            },
        })
    else:
        conda_exe_path = join(conda_prefix, 'bin', 'conda')
        conda_env_exe_path = join(conda_prefix, 'bin', 'conda-env')

    plan.append({
        'function': make_entry_point.__name__,
        'kwargs': {
            'target_path': conda_exe_path,
            'module': 'conda.cli',
            'func': 'main',
        },
    })
    plan.append({
        'function': make_entry_point.__name__,
        'kwargs': {
            'target_path': conda_env_exe_path,
            'module': 'conda_env.cli.main',
            'func': 'main',
        },
    })


def run_plan(plan):
    for step in plan:
        previous_result = step.get('result', None)
        if previous_result in (Result.MODIFIED, Result.NO_CHANGE):
            continue
        try:
            result = globals()[step['function']](*step.get('args', ()), **step.get('kwargs', {}))
        except (IOError, OSError) as e:
            log.debug("%s: %r", step['function'], e, exc_info=True)
            result = Result.NEEDS_SUDO
        step['result'] = result


def run_plan_elevated(plan):
    if any(step['result'] == Result.NEEDS_SUDO for step in plan):
        stdin = json.dumps(plan)
        result = subprocess_call(
            'sudo %s -m conda.core.initialize' % sys.executable,
            env={},
            cwd=os.getcwd(),
            stdin=stdin,
        )
        stderr = result.stderr.strip()
        if stderr:
            sys.stderr.write(stderr)
            sys.stderr.write('\n')

        _plan = json.loads(result.stdout.strip())
        del plan[:]
        plan.extend(_plan)


def run_plan_from_stdin():
    stdin = sys.stdin.read().strip()
    plan = json.loads(stdin)
    run_plan(plan)
    sys.stdout.write(json.dumps(plan))


def print_plan_results(plan, stream=sys.stdout):
    for step in plan:
        print("%s\n  %s\n" % (step['kwargs']['target_path'], step['result']), file=stream)

    changed = any(step['result'] == Result.MODIFIED for step in plan)
    if changed:
        print("\n==> For changes to take effect, close and re-open your current shell. <==\n", file=stream)
    else:
        print("No action taken.", file=stream)


def make_entry_point(target_path, module, func):
    # target_path: join(conda_prefix, 'bin', 'conda')
    conda_ep_path = target_path

    if isfile(conda_ep_path):
        with open(conda_ep_path) as fh:
            original_ep_content = fh.read()
    else:
        original_ep_content = ""

    if on_win:
        # no shebang needed on windows
        new_ep_content = ""
    else:
        new_ep_content = "#!" + join(dirname(target_path), 'python')

    new_ep_content += dals("""
    # -*- coding: utf-8 -*-

    if __name__ == '__main__':
        import sys
        from %(module)s import %(func)s
        sys.exit(%(func)s())
    """) % {
        'module': module,
        'func': func,
    }

    if new_ep_content != original_ep_content:
        mkdir_p(dirname(conda_ep_path))
        with open(conda_ep_path, 'w') as fdst:
            fdst.write(new_ep_content)
        if not on_win:
            make_executable(new_ep_content)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def make_entry_point_exe(target_path):
    # target_path: join(conda_prefix, 'Scripts', 'conda.exe')
    exe_path = target_path
    source_exe_path = join(CONDA_PACKAGE_ROOT, 'shell', 'cli-%d.exe' % context.bits)
    if isfile(exe_path):
        if compute_md5sum(exe_path) == compute_md5sum(source_exe_path):
            return Result.NO_CHANGE

    create_hard_link_or_copy(source_exe_path, exe_path)
    return Result.MODIFIED


def init_conda_sh(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'etc', 'profile.d', 'conda.sh')
    conda_sh_base_path = target_path
    conda_sh_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'profile.d', 'conda.sh')

    if isfile(conda_sh_base_path):
        with open(conda_sh_base_path) as fh:
            original_conda_sh = fh.read()
    else:
        original_conda_sh = ""

    if on_win:
        win_conda_exe = join(conda_prefix, 'Scripts', 'conda.exe')
        new_conda_sh = "_CONDA_EXE=\"$(cygpath '%s')\"\n" % win_conda_exe
    else:
        new_conda_sh = '_CONDA_EXE="%s"\n' % join(conda_prefix, 'bin', 'conda')
    with open(conda_sh_src_path) as fsrc:
        new_conda_sh += fsrc.read()

    if new_conda_sh != original_conda_sh:
        mkdir_p(dirname(conda_sh_base_path))
        with open(conda_sh_base_path, 'w') as fdst:
            fdst.write(new_conda_sh)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def init_sh_user(target_path, conda_prefix, auto_activate):
    # target_path: ~/.bash_profile
    user_rc_path = target_path
    conda_sh_base_path = join(conda_prefix, 'etc', 'profile.d', 'conda.sh')

    with open(user_rc_path) as fh:
        rc_content = fh.read()

    rc_original_content = rc_content

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

    rc_content = re.sub(
        r"^[ \t]*(export PATH=['\"]%s:\$PATH['\"])[ \t]*$" % re.escape(join(conda_prefix, 'bin')),
        r"# \1  # modified by conda initialize",
        rc_content,
        flags=re.MULTILINE,
    )
    rc_content = re.sub(
        r"^[ \t]*[^#\n]?[ \t]*((?:source|\.) .*\/etc\/profile\.d\/conda\.sh)[ \t]*$",
        r"# \1  # modified by conda initialize",
        rc_content,
        flags=re.MULTILINE,
    )
    rc_content = re.sub(
        r"^# >>> conda initialize >>>$([\s\S]*?)# <<< conda initialize <<<$",
        conda_initialize_content,
        rc_content,
        flags=re.MULTILINE,
    )

    if "# >>> conda initialize >>>" not in rc_content:
        rc_content += '\n%s\n' % conda_initialize_content

    if rc_content != rc_original_content:
        with open(user_rc_path, 'w') as fh:
            fh.write(rc_content)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def init_sh_system(target_path, conda_prefix):
    # target_path: '/etc/profile.d/conda.sh'
    conda_sh_system_path = target_path
    conda_sh_base_path = join(conda_prefix, 'etc', 'profile.d', 'conda.sh')

    if exists(conda_sh_system_path):
        with open(conda_sh_system_path) as fh:
            conda_sh_system_contents = fh.read()
    else:
        conda_sh_system_contents = ""
    with open(conda_sh_base_path) as fh:
        conda_sh_contents = fh.read()
    if conda_sh_system_contents != conda_sh_contents:
        if lexists(conda_sh_system_path):
            rm_rf(conda_sh_system_path)
        mkdir_p(dirname(conda_sh_system_path))
        create_soft_link_or_copy(conda_sh_base_path, conda_sh_system_path)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def init_sh_system_activate(target_path, auto_activate):
    # target_path: '/etc/profile.d/conda_activate_base.sh'
    conda_activate_sh_path = target_path
    if isinstance(auto_activate, string_types):
        auto_activate = boolify(auto_activate)
    if auto_activate:
        if exists(conda_activate_sh_path):
            with open(conda_activate_sh_path) as fh:
                conda_activate_sh_contents = fh.read()
        else:
            conda_activate_sh_contents = ""
        conda_activate_sh_final_contents = 'conda activate base\n'

        if conda_activate_sh_final_contents != conda_activate_sh_contents:
            with open(conda_activate_sh_path, 'w') as fh:
                fh.write(conda_activate_sh_final_contents)
                return Result.MODIFIED
        else:
            return Result.NO_CHANGE

    else:
        if lexists(conda_activate_sh_path):
            make_writable(conda_activate_sh_path)
            os.unlink(conda_activate_sh_path)
            return Result.MODIFIED
        else:
            return Result.NO_CHANGE


def init_conda_bat(target_path):
    # target_path: join(sys.prefix, 'Library', 'bin', 'conda.bat')
    conda_bat_dst_path = target_path
    conda_bat_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'Library', 'bin', 'conda.bat')

    if isfile(conda_bat_dst_path):
        with open(conda_bat_dst_path) as fh:
            original_conda_bat = fh.read()
    else:
        original_conda_bat = ""

    new_conda_bat = '@SET "_CONDA_EXE=%s"\n' % join(sys.prefix, 'Scripts', 'conda.exe')
    with open(conda_bat_src_path) as fsrc:
        new_conda_bat += fsrc.read()

    if new_conda_bat != original_conda_bat:
        mkdir_p(dirname(conda_bat_dst_path))
        with open(conda_bat_dst_path, 'w') as fdst:
            fdst.write(new_conda_bat)
            return Result.MODIFIED
    else:
        return Result.NO_CHANGE

    # TODO: use menuinst to create shortcuts


def init_conda_fish(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'etc', 'fish', 'conf.d', 'conda.fish')
    conda_fish_base_path = target_path
    conda_fish_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'fish', 'conf.d', 'conda.fish')

    if isfile(conda_fish_base_path):
        with open(conda_fish_base_path) as fh:
            original_conda_fish = fh.read()
    else:
        original_conda_fish = ""

    if on_win:
        new_conda_fish = 'set _CONDA_ROOT (cygpath %s)\n' % conda_prefix
        new_conda_fish += 'set _CONDA_EXE (cygpath %s)\n' % join(conda_prefix, 'Scripts', 'conda.exe')
    else:
        new_conda_fish = 'set _CONDA_ROOT "%s"\n' % conda_prefix
        new_conda_fish += 'set _CONDA_EXE "%s"\n' % join(conda_prefix, 'bin', 'conda')

    with open(conda_fish_src_path) as fsrc:
        new_conda_fish += fsrc.read()

    if new_conda_fish != original_conda_fish:
        mkdir_p(dirname(conda_fish_base_path))
        with open(conda_fish_base_path, 'w') as fdst:
            fdst.write(new_conda_fish)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def init_conda_xsh(target_path, conda_prefix):
    # target_path: join(site_packages_dir, 'xonsh', 'conda.xsh')
    conda_xsh_base_path = target_path
    conda_xsh_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'conda.xsh')

    if isfile(conda_xsh_base_path):
        with open(conda_xsh_base_path) as fh:
            original_conda_xsh = fh.read()
    else:
        original_conda_xsh = ""

    if on_win:
        new_conda_xsh = '_CONDA_EXE = "%s"\n' % join(conda_prefix, 'Scripts', 'conda.exe')
    else:
        new_conda_xsh = '_CONDA_EXE = "%s"\n' % join(conda_prefix, 'bin', 'conda')

    with open(conda_xsh_src_path) as fsrc:
        new_conda_xsh += fsrc.read()

    if new_conda_xsh != original_conda_xsh:
        mkdir_p(dirname(conda_xsh_base_path))
        with open(conda_xsh_base_path, 'w') as fdst:
            fdst.write(new_conda_xsh)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def init_conda_csh(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'etc', 'profile.d', 'conda.csh')

    conda_csh_base_path = target_path
    conda_csh_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'profile.d', 'conda.csh')

    if isfile(conda_csh_base_path):
        with open(conda_csh_base_path) as fh:
            original_conda_csh = fh.read()
    else:
        original_conda_csh = ""

    if on_win:
        new_conda_csh = 'setenv _CONDA_ROOT `cygpath %s`\n' % conda_prefix
        new_conda_csh += 'setenv _CONDA_EXE `cygpath %s`\n' % join(conda_prefix, 'Scripts', 'conda.exe')
    else:
        new_conda_csh = 'setenv _CONDA_ROOT "%s"\n' % conda_prefix
        new_conda_csh += 'setenv _CONDA_EXE "%s"\n' % join(conda_prefix, 'bin', 'conda')

    with open(conda_csh_src_path) as fsrc:
        new_conda_csh += fsrc.read()

    if new_conda_csh != original_conda_csh:
        mkdir_p(dirname(conda_csh_base_path))
        with open(conda_csh_base_path, 'w') as fdst:
            fdst.write(new_conda_csh)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE



def remove_conda_sp_dir(site_packages_dir):
    for path in glob(join(site_packages_dir, "conda*.egg")):
        print("rm -rf %s" % path, file=sys.stderr)
        rm_rf(path)

    if isfile(join(site_packages_dir, "conda.egg-link")):
        print("rm -rf %s" % join(site_packages_dir, "conda.egg-link"))
        rm_rf(join(site_packages_dir, "conda.egg-link"))
    if isfile(join(site_packages_dir, "conda")):
        print("rm -rf %s" % join(site_packages_dir, "conda"))
        rm_rf(join(site_packages_dir, "conda"))
    if isfile(join(site_packages_dir, "conda_env")):
        print("rm -rf %s" % join(site_packages_dir, "conda_env"))
        rm_rf(join(site_packages_dir, "conda_env"))


def make_conda_pth(target_path, conda_source_dir):
    # target_path: join(site_packages_dir, 'conda.pth')
    conda_pth_path = target_path
    conda_pth_contents = conda_source_dir

    if isfile(conda_pth_path):
        with open(conda_pth_path) as fh:
            conda_pth_contents_old = fh.read()
    else:
        conda_pth_contents_old = ""

    if conda_pth_contents_old != conda_pth_contents:
        with open(conda_pth_path, 'w') as fh:
            fh.write(conda_pth_contents)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


if __name__ == "__main__":
    run_plan_from_stdin()


