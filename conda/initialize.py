# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
import json
from logging import getLogger
import os
from os.path import dirname, exists, isdir, isfile, join
from random import randint
import re
import sys

from . import CONDA_PACKAGE_ROOT
from ._vendor.auxlib.ish import dals
from .common.compat import on_mac, on_win, open
from .common.path import expand, get_python_short_path, get_python_site_packages_short_path, \
    win_path_ok
from .gateways.disk.create import create_hard_link_or_copy, mkdir_p
from .gateways.disk.delete import rm_rf
from .gateways.disk.link import lexists
from .gateways.disk.permissions import make_executable
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
    assert not any(step['result'] == Result.NEEDS_SUDO for step in plan)
    print_plan_results(plan)


def initialize(conda_prefix, shells, for_user, for_system):
    plan = make_initialize_plan(conda_prefix, shells, for_user, for_system)
    run_plan(plan)
    run_plan_elevated(plan)
    print_plan_results(plan)


def _get_python_info(prefix):
    python_exe = join(prefix, get_python_short_path())
    result = subprocess_call("%s --version" % python_exe)
    stdout, stderr = result.stdout.strip(), result.stderr.strip()
    if stderr:
        python_version = stderr.split()[1]
    elif stdout:  # pragma: no cover
        python_version = stdout.split()[1]
    else:  # pragma: no cover
        raise ValueError("No python version information available.")

    site_packages_dir = join(prefix,
                             win_path_ok(get_python_site_packages_short_path(python_version)))
    return python_exe, python_version, site_packages_dir


def initialize_dev(shell, dev_env_prefix=None, conda_source_dir=None):
    # > alias conda-dev='eval "$(python -m conda init --dev)"'
    # > eval "$(python -m conda init --dev)"

    dev_env_prefix = expand(dev_env_prefix or sys.prefix)
    conda_source_dir = expand(conda_source_dir or os.getcwd())

    python_exe, python_version, site_packages_dir = _get_python_info(dev_env_prefix)

    if not isfile(join(conda_source_dir, 'conda', '__init__.py')):
        print("Directory is not a conda source root: %s" % conda_source_dir, file=sys.stderr)
        return 1

    plan = []
    plan.append({
        'function': remove_conda_in_sp_dir.__name__,
        'kwargs': {
            'target_path': site_packages_dir,
        },
    })
    plan.append({
        'function': make_conda_pth.__name__,
        'kwargs': {
            'target_path': join(site_packages_dir, '50-conda-dev.pth'),
            'conda_source_dir': conda_source_dir,
        },
    })

    run_plan(plan)
    if shell == "bash":
        builder = [
            "export PYTHON_MAJOR_VERSION='%s'" % python_version[0],
            "export TEST_PLATFORM='%s'" % ('win' if sys.platform.startswith('win') else 'unix'),
            "export PYTHONHASHSEED='%d'" % randint(0, 4294967296),
            "export _CONDA_ROOT='%s'" % conda_source_dir,
            ". conda/shell/etc/profile.d/conda.sh",
            "conda activate '%s'" % dev_env_prefix,
        ]
        print("\n".join(builder))
    else:
        raise NotImplementedError()


def make_install_plan(conda_prefix):
    python_exe, python_version, site_packages_dir = _get_python_info(conda_prefix)

    plan = []

    # ######################################
    # executables
    # ######################################
    if on_win:
        conda_exe_path = join(conda_prefix, 'Scripts', 'conda-script.py')
        conda_env_exe_path = join(conda_prefix, 'Scripts', 'conda-env-script.py')
        plan.append({
            'function': make_entry_point_exe.__name__,
            'kwargs': {
                'target_path': join(conda_prefix, 'Scripts', 'conda.exe'),
                'conda_prefix': conda_prefix,
            },
        })
        plan.append({
            'function': make_entry_point_exe.__name__,
            'kwargs': {
                'target_path': join(conda_prefix, 'Scripts', 'conda-env.exe'),
                'conda_prefix': conda_prefix,
            },
        })
    else:
        conda_exe_path = join(conda_prefix, 'bin', 'conda')
        conda_env_exe_path = join(conda_prefix, 'bin', 'conda-env')

    plan.append({
        'function': make_entry_point.__name__,
        'kwargs': {
            'target_path': conda_exe_path,
            'conda_prefix': conda_prefix,
            'module': 'conda.cli',
            'func': 'main',
        },
    })
    plan.append({
        'function': make_entry_point.__name__,
        'kwargs': {
            'target_path': conda_env_exe_path,
            'conda_prefix': conda_prefix,
            'module': 'conda_env.cli.main',
            'func': 'main',
        },
    })

    # ######################################
    # shell wrappers
    # ######################################
    if on_win:
        plan.append({
            'function': init_conda_bat.__name__,
            'kwargs': {
                'target_path': join(sys.prefix, 'Library', 'bin', 'conda.bat'),
                'conda_prefix': conda_prefix,
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


def make_initialize_plan(conda_prefix, shells, for_user, for_system):
    plan = make_install_plan(conda_prefix)

    shells = set(shells)
    if shells & {'bash', 'zsh'}:
        if 'bash' in shells and for_user:
            bashrc_path = expand(join('~', '.bash_profile' if on_mac else '.bashrc'))
            plan.append({
                'function': init_sh_user.__name__,
                'kwargs': {
                    'target_path': bashrc_path,
                    'conda_prefix': conda_prefix,
                },
            })

        if 'zsh' in shells and for_user:
            zshrc_path = expand(join('~', '.zshrc'))
            plan.append({
                'function': init_sh_user.__name__,
                'kwargs': {
                    'target_path': zshrc_path,
                    'conda_prefix': conda_prefix,
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

    return plan


def run_plan(plan):
    for step in plan:
        previous_result = step.get('result', None)
        if previous_result in (Result.MODIFIED, Result.NO_CHANGE):
            continue
        try:
            result = globals()[step['function']](*step.get('args', ()), **step.get('kwargs', {}))
        except (IOError, OSError) as e:
            log.error("%s: %r", step['function'], e, exc_info=True)
            result = Result.NEEDS_SUDO
        step['result'] = result


def run_plan_elevated(plan):
    if any(step['result'] == Result.NEEDS_SUDO for step in plan):
        stdin = json.dumps(plan)
        if on_win:
            # https://github.com/ContinuumIO/menuinst/blob/master/menuinst/windows/win_elevate.py  # no stdin / stdout / stderr pipe support  # NOQA
            # https://github.com/saltstack/salt-windows-install/blob/master/deps/salt/python/App/Lib/site-packages/win32/Demos/pipes/runproc.py  # NOQA
            # https://github.com/twonds/twisted/blob/master/twisted/internet/_dumbwin32proc.py
            # https://stackoverflow.com/a/19982092/2127762
            # https://www.codeproject.com/Articles/19165/Vista-UAC-The-Definitive-Guide
            raise NotImplementedError("Windows. Blah. Run as Administrator on your own.")
        else:
            result = subprocess_call(
                'sudo %s -m conda.initialize' % sys.executable,
                env={},
                path=os.getcwd(),
                stdin=stdin
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
        print("\n==> For changes to take effect, close and re-open your current shell. <==\n",
              file=stream)
    else:
        print("No action taken.", file=stream)


def make_entry_point(target_path, conda_prefix, module, func):
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
        new_ep_content = "#!%s\n" % join(conda_prefix, get_python_short_path())

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
            make_executable(conda_ep_path)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def make_entry_point_exe(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'Scripts', 'conda.exe')
    exe_path = target_path
    bits = 8 * tuple.__itemsize__
    source_exe_path = join(CONDA_PACKAGE_ROOT, 'shell', 'cli-%d.exe' % bits)
    if isfile(exe_path):
        if compute_md5sum(exe_path) == compute_md5sum(source_exe_path):
            return Result.NO_CHANGE

    if not isdir(dirname(exe_path)):
        mkdir_p(dirname(exe_path))
    create_hard_link_or_copy(source_exe_path, exe_path)
    return Result.MODIFIED


def conda_exe(conda_prefix):
    if on_win:
        return "$(cygpath '%s')" % join(conda_prefix, 'Scripts', 'conda.exe')
    else:
        return join(conda_prefix, 'bin', 'conda')


def init_conda_sh(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'etc', 'profile.d', 'conda.sh')
    conda_sh_base_path = target_path

    if isfile(conda_sh_base_path):
        with open(conda_sh_base_path) as fh:
            original_conda_sh = fh.read()
    else:
        original_conda_sh = ""

    from .hook import Hook
    new_conda_sh = Hook(conda_prefix, False).posix()

    if new_conda_sh != original_conda_sh:
        mkdir_p(dirname(conda_sh_base_path))
        with open(conda_sh_base_path, 'w') as fdst:
            fdst.write(new_conda_sh)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def init_sh_user(target_path, conda_prefix):
    # target_path: ~/.bash_profile
    user_rc_path = target_path

    with open(user_rc_path) as fh:
        rc_content = fh.read()

    rc_original_content = rc_content

    conda_initialize_content = (
        '# >>> conda initialize >>>\n'
        'eval "$(\'%s\' hook posix)"\n'
        '# <<< conda initialize <<<\n'
    ) % conda_exe(conda_prefix)

    rc_content = re.sub(
        r"^[ \t]*(export PATH=['\"]%s:\$PATH['\"])[ \t]*$" % re.escape(join(conda_prefix, 'bin')),
        r"# \1  # modified by conda initialize",
        rc_content,
        flags=re.MULTILINE,
    )
    rc_content = re.sub(
        r"^[ \t]*[^#\n]?[ \t]*((?:source|\.) .*\/etc\/profile\.d\/conda\.sh).*?\n",
        r"# \1  # modified by conda initialize\n",
        rc_content,
        flags=re.MULTILINE,
    )
    rc_content = re.sub(
        r"^# >>> conda initialize >>>$([\s\S]*?)# <<< conda initialize <<<\n$",
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

    if exists(conda_sh_system_path):
        with open(conda_sh_system_path) as fh:
            conda_sh_system_contents = fh.read()
    else:
        conda_sh_system_contents = ""
    conda_sh_contents = 'eval "$(\'%s\' hook posix)"\n' % conda_exe(conda_prefix)
    if conda_sh_system_contents != conda_sh_contents:
        if lexists(conda_sh_system_path):
            rm_rf(conda_sh_system_path)
        mkdir_p(dirname(conda_sh_system_path))
        with open(conda_sh_system_path, 'w') as fh:
            fh.write(conda_sh_contents)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def init_conda_bat(target_path, conda_prefix):
    # target_path: join(sys.prefix, 'Library', 'bin', 'conda.bat')
    conda_bat_dst_path = target_path
    conda_bat_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'Library', 'bin', 'conda.bat')

    if isfile(conda_bat_dst_path):
        with open(conda_bat_dst_path) as fh:
            original_conda_bat = fh.read()
    else:
        original_conda_bat = ""

    new_conda_bat = '@SET "_CONDA_EXE=%s"\n' % join(conda_prefix, 'Scripts', 'conda.exe')
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
        new_conda_fish += 'set _CONDA_EXE (cygpath %s)\n' % join(conda_prefix,
                                                                 'Scripts', 'conda.exe')
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
        new_conda_csh += 'setenv _CONDA_EXE `cygpath %s`\n' % join(conda_prefix,
                                                                   'Scripts', 'conda.exe')
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


def remove_conda_in_sp_dir(target_path):
    # target_path: site_packages_dir
    site_packages_dir = target_path
    for path in glob(join(site_packages_dir, "conda*.egg")):
        print("rm -rf %s" % path, file=sys.stderr)
        rm_rf(path)
    others = (
        "conda",
        "conda.egg-link",
        "conda_env",
    )
    for other in others:
        path = join(site_packages_dir, other)
        if isfile(path):
            print("rm -rf %s" % path)
            rm_rf(path)


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
