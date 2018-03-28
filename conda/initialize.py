# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import ENOENT
from glob import glob
import json
from logging import getLogger
import os
from os.path import dirname, exists, expanduser, isdir, isfile, join
from random import randint
import re
import sys
from tempfile import NamedTemporaryFile

from . import CONDA_PACKAGE_ROOT
from ._vendor.auxlib.ish import dals
from .common.compat import PY2, on_mac, on_win, open, ensure_binary, ensure_unicode
from .common.path import (expand, get_python_short_path, get_python_site_packages_short_path,
                          win_path_ok)
from .gateways.disk.create import copy, mkdir_p
from .gateways.disk.delete import rm_rf
from .gateways.disk.link import lexists
from .gateways.disk.permissions import make_executable
from .gateways.disk.read import compute_md5sum
from .gateways.subprocess import subprocess_call

if on_win:
    if PY2:
        import _winreg as winreg
    else:
        import winreg
    from menuinst.winshortcut import create_shortcut


log = getLogger(__name__)

ALL_SHELLS = (
    'cmd_exe',
    'bash',
    'zsh',
    'fish',
    'tcsh',
    'xonsh',
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


def initialize(conda_prefix, shells, for_user, for_system, desktop_prompt):
    plan1 = []
    if os.getenv('CONDA_PIP_UNINITIALIZED') == 'true':
        plan1 = make_install_plan(conda_prefix)
        run_plan(plan1)
        run_plan_elevated(plan1)
        # TODO: make sure this all succeeded

    plan2 = make_initialize_plan(conda_prefix, shells, for_user, for_system, desktop_prompt)
    run_plan(plan2)
    run_plan_elevated(plan2)
    print_plan_results(plan1 + plan2)


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


def initialize_dev(shell, dev_env_prefix=None, conda_source_root=None):
    # > alias conda-dev='eval "$(python -m conda init --dev)"'
    # > eval "$(python -m conda init --dev)"

    dev_env_prefix = expand(dev_env_prefix or sys.prefix)
    conda_source_root = expand(conda_source_root or os.getcwd())

    python_exe, python_version, site_packages_dir = _get_python_info(dev_env_prefix)

    if not isfile(join(conda_source_root, 'conda', '__main__.py')):
        print("Directory is not a conda source root: %s" % conda_source_root, file=sys.stderr)
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
            'target_path': join(site_packages_dir, 'conda-dev.pth'),
            'conda_source_root': conda_source_root,
        },
    })

    run_plan(plan)
    if any(step['result'] == Result.NEEDS_SUDO for step in plan):
        print("Operation failed.", file=sys.stderr)
        return 1

    if shell == "bash":
        builder = [
            "export PYTHON_MAJOR_VERSION='%s'" % python_version[0],
            "export TEST_PLATFORM='%s'" % ('win' if sys.platform.startswith('win') else 'unix'),
            "export PYTHONHASHSEED='%d'" % randint(0, 4294967296),
            "export _CONDA_ROOT='%s'" % conda_source_root,
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
            'function': install_conda_bat.__name__,
            'kwargs': {
                'target_path': join(conda_prefix, 'Library', 'bin', 'conda.bat'),
                'conda_prefix': conda_prefix,
            },
        })
        plan.append({
            'function': install_condacmd_conda_bat.__name__,
            'kwargs': {
                'target_path': join(conda_prefix, 'condacmd', 'conda.bat'),
                'conda_prefix': conda_prefix,
            },
        })
        plan.append({
            'function': install_condacmd_hook_bat.__name__,
            'kwargs': {
                'target_path': join(conda_prefix, 'condacmd', 'conda-hook.bat'),
                'conda_prefix': conda_prefix,
            },
        })

    plan.append({
        'function': install_conda_sh.__name__,
        'kwargs': {
            'target_path': join(conda_prefix, 'etc', 'profile.d', 'conda.sh'),
            'conda_prefix': conda_prefix,
        },
    })
    plan.append({
        'function': install_conda_fish.__name__,
        'kwargs': {
            'target_path': join(conda_prefix, 'etc', 'fish', 'conf.d', 'conda.fish'),
            'conda_prefix': conda_prefix,
        },
    })
    plan.append({
        'function': install_conda_xsh.__name__,
        'kwargs': {
            'target_path': join(site_packages_dir, 'xonsh', 'conda.xsh'),
            'conda_prefix': conda_prefix,
        },
    })
    plan.append({
        'function': install_conda_csh.__name__,
        'kwargs': {
            'target_path': join(conda_prefix, 'etc', 'profile.d', 'conda.csh'),
            'conda_prefix': conda_prefix,
        },
    })
    return plan


def make_initialize_plan(conda_prefix, shells, for_user, for_system, desktop_prompt):
    plan = []
    shells = set(shells)
    if shells & {'bash', 'zsh'}:
        if 'bash' in shells and for_user:
            bashrc_path = expand(join('~', '.bash_profile' if on_mac else '.bashrc'))
            plan.append({
                'function': init_sh_user.__name__,
                'kwargs': {
                    'target_path': bashrc_path,
                    'conda_prefix': conda_prefix,
                    'shell': 'bash',
                },
            })

        if 'zsh' in shells and for_user:
            zshrc_path = expand(join('~', '.zshrc'))
            plan.append({
                'function': init_sh_user.__name__,
                'kwargs': {
                    'target_path': zshrc_path,
                    'conda_prefix': conda_prefix,
                    'shell': 'zsh',
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

    if shells & {'fish', }:
        raise NotImplementedError()

    if shells & {'tcsh', }:
        raise NotImplementedError()

    if shells & {'powershell', }:
        raise NotImplementedError()

    if shells & {'cmd_exe', }:
        # TODO: make sure cmd_exe and cmd.exe are consistently used; choose one
        if for_user:
            plan.append({
                'function': init_cmd_exe_user.__name__,
                'kwargs': {
                    'conda_prefix': conda_prefix,
                },
            })

    if on_win and desktop_prompt:
        plan.append({
            'function': install_conda_shortcut.__name__,
            'kwargs': {
                'target_path': join(conda_prefix, 'condacmd', 'Conda Prompt.lnk'),
                'conda_prefix': conda_prefix,
            },
        })
        plan.append({
            'function': install_conda_shortcut.__name__,
            'kwargs': {
                'target_path': join(os.environ["HOMEPATH"], "Desktop", "Conda Prompt.lnk"),
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
        if on_win:
            from menuinst.win_elevate import runAsAdmin
            # https://github.com/ContinuumIO/menuinst/blob/master/menuinst/windows/win_elevate.py  # no stdin / stdout / stderr pipe support  # NOQA
            # https://github.com/saltstack/salt-windows-install/blob/master/deps/salt/python/App/Lib/site-packages/win32/Demos/pipes/runproc.py  # NOQA
            # https://github.com/twonds/twisted/blob/master/twisted/internet/_dumbwin32proc.py
            # https://stackoverflow.com/a/19982092/2127762
            # https://www.codeproject.com/Articles/19165/Vista-UAC-The-Definitive-Guide

            # from menuinst.win_elevate import isUserAdmin, runAsAdmin
            # I do think we can pipe to stdin, so we're going to have to write to a temp file and read in the elevated process  # NOQA

            temp_path = None
            try:
                with NamedTemporaryFile('w+b', suffix='.json', delete=False) as tf:
                    # the default mode is 'w+b', and universal new lines don't work in that mode
                    tf.write(ensure_binary(json.dumps(plan, ensure_ascii=False)))
                    temp_path = tf.name
                rc = runAsAdmin('%s -m conda.initialize \'%s\'' % (sys.executable, temp_path))
                assert rc == 0

                with open(temp_path) as fh:
                    _plan = json.loads(ensure_unicode(fh.read()))
            finally:
                if temp_path and lexists(temp_path):
                    rm_rf(temp_path)

        else:
            stdin = json.dumps(plan)
            result = subprocess_call(
                'sudo %s -m conda.initialize' % sys.executable,
                env={},
                path=os.getcwd(),
                stdin=stdin
            )
            stderr = result.stderr.strip()
            if stderr:
                print(stderr, file=sys.stderr)
            _plan = json.loads(result.stdout.strip())

        del plan[:]
        plan.extend(_plan)


def run_plan_from_stdin():
    stdin = sys.stdin.read().strip()
    plan = json.loads(stdin)
    run_plan(plan)
    sys.stdout.write(json.dumps(plan))


def run_plan_from_temp_file(temp_path):
    with open(temp_path) as fh:
        plan = json.loads(ensure_unicode(fh.read()))
    run_plan(plan)
    with open(temp_path, 'w+b') as fh:
        fh.write(ensure_binary(json.dumps(plan, ensure_ascii=False)))


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

    conda_extra = dals("""
    # Before any more imports, leave cwd out of sys.path for internal 'conda shell.*' commands.
    # see https://github.com/conda/conda/issues/6549
    if len(sys.argv) > 1 and sys.argv[1].startswith('shell.') and sys.path and sys.path[0] == '':
        # The standard first entry in sys.path is an empty string,
        # and os.path.abspath('') expands to os.getcwd().
        del sys.path[0]
    """)

    new_ep_content += dals("""
    # -*- coding: utf-8 -*-
    import sys
    %(extra)s
    if __name__ == '__main__':
        from %(module)s import %(func)s
        sys.exit(%(func)s())
    """) % {
        'extra': conda_extra if module == 'conda.cli' else '',
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
    # prefer copy() over create_hard_link_or_copy() because of windows file deletion issues
    # with open processes
    copy(source_exe_path, exe_path)
    return Result.MODIFIED


def _conda_exe(conda_prefix):
    if on_win:
        return "$(cygpath '%s')" % join(conda_prefix, 'Scripts', 'conda.exe')
    else:
        return join(conda_prefix, 'bin', 'conda')


def install_conda_shortcut(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'condacmd', 'Conda Prompt.lnk')
    # target: join(os.environ["HOMEPATH"], "Desktop", "Conda Prompt.lnk")
    icon_path = join(CONDA_PACKAGE_ROOT, 'shell', 'conda_icon.ico')

    args = (
        '/K',
        '"%s"' % join(conda_prefix, 'condacmd', 'conda-hook.bat'),
    )
    # The API for the call to 'create_shortcut' has 3
    # required arguments (path, description, filename)
    # and 4 optional ones (args, working_dir, icon_path, icon_index).
    create_shortcut(
        "%windir%\\System32\\cmd.exe",
        "Conda Prompt",
        '' + target_path,
        ' '.join(args),
        '' + expanduser('~'),
        '' + icon_path,
    )


def _install_file(target_path, file_content):
    if isfile(target_path):
        with open(target_path) as fh:
            original_content = fh.read()
    else:
        original_content = ""

    new_content = file_content

    if new_content != original_content:
        mkdir_p(dirname(target_path))
        with open(target_path, 'w') as fdst:
            fdst.write(new_content)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def install_conda_sh(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'etc', 'profile.d', 'conda.sh')
    from .activate import PosixActivator
    file_content = PosixActivator().hook(auto_activate_base=False)
    return _install_file(target_path, file_content)


def install_conda_bat(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'Library', 'bin', 'conda.bat')
    conda_bat_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'Library', 'bin', 'conda.bat')
    file_content = '@SET "_CONDA_EXE=%s"\n' % join(conda_prefix, 'Scripts', 'conda.exe')
    with open(conda_bat_src_path) as fsrc:
        file_content += fsrc.read()
    return _install_file(target_path, file_content)


def install_condacmd_conda_bat(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'condacmd', 'conda.bat')
    conda_bat_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'condacmd', 'conda.bat')
    with open(conda_bat_src_path) as fsrc:
        file_content = fsrc.read()
    return _install_file(target_path, file_content)


def install_condacmd_hook_bat(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'condacmd', 'conda-hook.bat')
    conda_bat_src_path = join(CONDA_PACKAGE_ROOT, 'shell', 'condacmd', 'conda-hook.bat')
    with open(conda_bat_src_path) as fsrc:
        file_content = fsrc.read()
    return _install_file(target_path, file_content)


def install_conda_fish(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'etc', 'fish', 'conf.d', 'conda.fish')
    from .activate import FishActivator
    file_content = FishActivator().hook(auto_activate_base=False)
    return _install_file(target_path, file_content)


def install_conda_xsh(target_path, conda_prefix):
    # target_path: join(site_packages_dir, 'xonsh', 'conda.xsh')
    from .activate import XonshActivator
    file_content = XonshActivator().hook(auto_activate_base=False)
    return _install_file(target_path, file_content)


def install_conda_csh(target_path, conda_prefix):
    # target_path: join(conda_prefix, 'etc', 'profile.d', 'conda.csh')
    from .activate import CshActivator
    file_content = CshActivator().hook(auto_activate_base=False)
    return _install_file(target_path, file_content)


def init_sh_user(target_path, conda_prefix, shell):
    # target_path: ~/.bash_profile
    user_rc_path = target_path

    with open(user_rc_path) as fh:
        rc_content = fh.read()

    rc_original_content = rc_content

    conda_initialize_content = (
        '# >>> conda initialize >>>\n'
        'eval "$(\'%s\' shell.%s hook)"\n'
        '# <<< conda initialize <<<\n'
    ) % (_conda_exe(conda_prefix), shell)

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
    conda_sh_contents = 'eval "$(\'%s\' shell.posix hook)"\n' % _conda_exe(conda_prefix)
    if conda_sh_system_contents != conda_sh_contents:
        if lexists(conda_sh_system_path):
            rm_rf(conda_sh_system_path)
        mkdir_p(dirname(conda_sh_system_path))
        with open(conda_sh_system_path, 'w') as fh:
            fh.write(conda_sh_contents)
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def init_cmd_exe_user(conda_prefix):
    # HKEY_LOCAL_MACHINE\Software\Microsoft\Command Processor\AutoRun
    # HKEY_CURRENT_USER\Software\Microsoft\Command Processor\AutoRun
    key_str = r'Software\Microsoft\Command Processor'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_str, 0, winreg.KEY_ALL_ACCESS)
    except EnvironmentError as e:
        if e.errno != ENOENT:
            raise
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_str)
    try:
        try:
            value = winreg.QueryValueEx(key, "AutoRun")
            prev_value = value[0].strip()
            value_type = value[1]
        except EnvironmentError as e:
            if e.errno != ENOENT:
                raise
            prev_value = ""
            value_type = winreg.REG_EXPAND_SZ

        # TODO: remove conda-hook.bat from prev_value

        hook_path = join(conda_prefix, 'condacmd', 'conda-hook.bat')
        new_value = "%s & %s" % (prev_value, hook_path) if prev_value else hook_path

        if prev_value != new_value:
            winreg.SetValueEx(key, "AutoRun", 0, value_type, new_value)
            return Result.MODIFIED
        else:
            return Result.NO_CHANGE
    finally:
        winreg.CloseKey(key)


def remove_conda_in_sp_dir(target_path):
    # target_path: site_packages_dir
    modified = False
    site_packages_dir = target_path
    for fn in glob(join(site_packages_dir, "conda*.egg")):
        print("rm -rf %s" % join(site_packages_dir, fn), file=sys.stderr)
        rm_rf(join(site_packages_dir, fn))
        modified = True
    for fn in glob(join(site_packages_dir, "conda.*")):
        print("rm -rf %s" % join(site_packages_dir, fn), file=sys.stderr)
        rm_rf(join(site_packages_dir, fn))
        modified = True
    others = (
        "conda",
        "conda.egg-link",
        "conda_env",
    )
    for other in others:
        path = join(site_packages_dir, other)
        if lexists(path):
            print("rm -rf %s" % path, file=sys.stderr)
            rm_rf(path)
            modified = True
    if modified:
        return Result.MODIFIED
    else:
        return Result.NO_CHANGE


def make_conda_pth(target_path, conda_source_dir):
    # target_path: join(site_packages_dir, 'conda-dev.pth')
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
    if on_win:
        temp_path = sys.argv[1]
        run_plan_from_temp_file(temp_path)
    else:
        run_plan_from_stdin()
