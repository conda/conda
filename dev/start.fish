#!/usr/bin/env fish
# NOTE: This script should be sourced! The shebang is only here to help syntax highlighters.

function cleanup
    set -e _ARCH
    set -e _BASEEXE
    set -e _CHANNEL_NAME
    set -e _CHOICE
    set -e _CMD
    set -e _DEFAULT_ARCH
    set -e _DEFAULT_DEVENV
    set -e _DEFAULT_DRYRUN
    set -e _DEFAULT_INSTALLER
    set -e _DEFAULT_MACH
    set -e _DEFAULT_PYTHON
    set -e _DEFAULT_UPDATE
    set -e _DEVENV
    set -e _DOWNLOAD_URL
    set -e _DRYRUN
    set -e _ENV
    set -e _ENVEXE
    set -e _INSTALLER
    set -e _INSTALLER_DISPLAY
    set -e _INSTALLER_FILE
    set -e _INSTALLER_INITIAL
    set -e _INSTALLER_TYPE
    set -e _MACH
    set -e _NAME
    set -e _PYTHON
    set -e _PYTHONEXE
    set -e _SCRIPT_PATH
    set -e _SHELL_TYPE
    set -e _SRC
    set -e _UPDATE
    set -e _UPDATED
end

function updating
    # check if explicitly updating or if 24 hrs since last update
    test "$_UPDATE" = "true" && return 0
    test -f "$_UPDATED" || return 0
    set current_time (date +%s)
    set file_time (date -r "$_UPDATED" +%s)
    set diff_time (math $current_time - $file_time)
    test $diff_time -lt 86400
end

cleanup

# get source path
set _SCRIPT_PATH (status filename)
set _SRC (dirname (dirname $_SCRIPT_PATH))
set _SRC (cd "$_SRC" 2>&1 > /dev/null; pwd -P)

# define default values
set _DEFAULT_PYTHON "3.10"
set _DEFAULT_INSTALLER "miniconda"
# $ uname -sm
# Linux x86_64
# Linux aarch64
# Darwin arm64
# ...
set _DEFAULT_MACH (uname)
set _DEFAULT_ARCH (uname -m)
set _DEFAULT_UPDATE "false"
set _DEFAULT_DEVENV "$_SRC/devenv"
set _DEFAULT_DRYRUN "false"

# parse args
set i 1
while test $i -le (count $argv)
    switch $argv[$i]
        case -p --python
            set _PYTHON $argv[(math $i + 1)]
            set i (math $i + 2)
        case -m --mach
            set _MACH $argv[(math $i + 1)]
            set i (math $i + 2)
        case -a --arch
            set _ARCH $argv[(math $i + 1)]
            set i (math $i + 2)
        case -i --installer
            set _INSTALLER_TYPE $argv[(math $i + 1)]
            set i (math $i + 2)
        case -u --update
            set _UPDATE "true"
            set i (math $i + 1)
        case -d --devenv
            set _DEVENV $argv[(math $i + 1)]
            set i (math $i + 2)
        case -n --dry-run
            set _DRYRUN "true"
            set i (math $i + 1)
        case -h --help
            echo "Usage: source $_SCRIPT_PATH [options]"
            echo ""
            echo "Options:"
            echo "  -p, --python    VERSION    Python version for the env to activate. (default: $_DEFAULT_PYTHON)"
            echo "  -i, --installer INSTALLER  Installer to use: miniconda or miniforge, can also be defined in ~/.condarc. (default: $_DEFAULT_INSTALLER)"
            echo "  -m, --mach      MACHINE    Machine type for the env to activate. (default: $_DEFAULT_MACH)"
            echo "  -a, --arch      ARCH       Architecture for the env to activate. (default: $_DEFAULT_ARCH)"
            echo "  -u, --update               Force update packages. (default: $_DEFAULT_UPDATE, update every 24 hours)"
            echo "  -d, --devenv    PATH       Path to base env install, can also be defined in ~/.condarc."
            echo "                             Path is appended with machine hardware name, see --mach. (default: $_DEFAULT_DEVENV)"
            echo "  -n, --dry-run              Display env to activate. (default: $_DEFAULT_DRYRUN)"
            echo "  -h, --help                 Display this."
            return 0
        case '*'
            set arg $argv[$i]
            if test (echo "$arg" | head -c 9) = "--python="
                set _PYTHON (echo "$arg" | tail -c +10)
                set i (math $i + 1)
            else if test (echo "$arg" | head -c 7) = "--mach="
                set _MACH (echo "$arg" | tail -c +8)
                set i (math $i + 1)
            else if test (echo "$arg" | head -c 7) = "--arch="
                set _ARCH (echo "$arg" | tail -c +8)
                set i (math $i + 1)
            else if test (echo "$arg" | head -c 12) = "--installer="
                set _INSTALLER_TYPE (echo "$arg" | tail -c +13)
                set i (math $i + 1)
            else if test (echo "$arg" | head -c 9) = "--devenv="
                set _DEVENV (echo "$arg" | tail -c +10)
                set i (math $i + 1)
            else
                echo "Error: unknown option $arg" >&2
                return 1
            end
    end
end

# fallback to default values
set _PYTHON (test -n "$_PYTHON" && echo "$_PYTHON" || echo "3.10")
# Note: _INSTALLER_TYPE is set explicitly or left empty for later processing
# $ uname -sm
# Linux x86_64
# Linux aarch64
# Darwin arm64
# ...
set _MACH (test -n "$_MACH" && echo "$_MACH" || echo "$_DEFAULT_MACH")
set _ARCH (test -n "$_ARCH" && echo "$_ARCH" || echo "$_DEFAULT_ARCH")
set _UPDATE (test -n "$_UPDATE" && echo "$_UPDATE" || echo "$_DEFAULT_UPDATE")
set _DRYRUN (test -n "$_DRYRUN" && echo "$_DRYRUN" || echo "$_DEFAULT_DRYRUN")

# read installer_type key from ~/.condarc if not explicitly set
if test -z "$_INSTALLER_TYPE" && test -f ~/.condarc
    set _INSTALLER_TYPE (grep "^installer_type:" ~/.condarc | tail -n 1 | sed -e "s/^.*:[[:space:]]*//" -e "s/[[:space:]]*\$//")
end

# prompt for installer type if still not specified
if test -z "$_INSTALLER_TYPE"
    echo "Choose conda installer:"
    echo "  1) miniconda (default - Anaconda defaults channel)"
    echo "  2) miniforge (conda-forge channel)"
    echo ""
    set _CHOICE (read -P "Enter choice [1]: ")
    switch $_CHOICE
        case 1 "" miniconda
            set _INSTALLER_TYPE "miniconda"
        case 2 miniforge
            set _INSTALLER_TYPE "miniforge"
        case '*'
            echo "Error: invalid choice '$_CHOICE'. Please run again and choose 1 or 2." >&2
            return 1
    end
end

# set default if still empty (shouldn't happen, but safety fallback)
set _INSTALLER_TYPE (test -n "$_INSTALLER_TYPE" && echo "$_INSTALLER_TYPE" || echo "$_DEFAULT_INSTALLER")

# validate installer type
switch $_INSTALLER_TYPE
    case miniconda miniforge
        # valid
    case '*'
        echo "Error: invalid installer type '$_INSTALLER_TYPE'. Must be 'miniconda' or 'miniforge'." >&2
        return 1
end

# read devenv key from ~/.condarc
if test -f ~/.condarc
    set _DEVENV (test -n "$_DEVENV" && echo "$_DEVENV" || echo (grep "^devenv:" ~/.condarc | tail -n 1 | sed -e "s/^.*:[[:space:]]*//" -e "s/[[:space:]]*\$//"))
end
# fallback to devenv in source default
set _DEVENV (test -n "$_DEVENV" && echo "$_DEVENV" || echo "$_DEFAULT_DEVENV")
# tilde expansion
set _DEVENV (string replace --regex '^~' "$HOME" "$_DEVENV")
# include OS
set _DEVENV "$_DEVENV/$_MACH/$_ARCH"
# ensure exists and absolute path
if test "$_DRYRUN" = "false"
    mkdir -p "$_DEVENV"
    set _DEVENV (cd "$_DEVENV" 2>&1 > /dev/null; pwd -P)
end
# installer location
set _INSTALLER (dirname (dirname "$_DEVENV"))

# other environment values
set _NAME "devenv-$_PYTHON-$_INSTALLER_TYPE"
set _ENV "$_DEVENV/envs/$_NAME"
set _UPDATED "$_ENV/.devenv-updated"
switch $_MACH
    case Darwin Linux
        set _BASEEXE "$_DEVENV/bin/conda"
        set _ENVEXE "$_ENV/bin/conda"
        set _PYTHONEXE "$_ENV/bin/python"
    case '*'
        set _BASEEXE "$_DEVENV/Scripts/conda.exe"
        set _ENVEXE "$_ENV/Scripts/conda.exe"
        set _PYTHONEXE "$_ENV/Scripts/python.exe"
end

# dryrun printout
if test "$_DRYRUN" = "true"
    echo "Python: $_PYTHON"
    echo "Installer: $_INSTALLER_TYPE"
    echo "Machine: $_MACH"
    echo "Architecture: $_ARCH"
    echo "Updating: "(updating && echo "[yes]" || echo "[no]")
    echo "Devenv: $_DEVENV "(test -e "$_DEVENV" && echo "[exists]" || echo "[pending]")
    echo ""
    echo "Name: $_NAME"
    echo "Path: $_ENV "(test -e "$_ENV" && echo "[exists]" || echo "[pending]")
    echo ""
    echo "Source: $_SRC"
    return 0
end

# deactivate any prior envs
if test -n "$CONDA_SHLVL" && test "$CONDA_SHLVL" -ne 0
    echo "Deactivating $CONDA_SHLVL environment(s)..."
    set deactivate_count 0
    while test -n "$CONDA_SHLVL" && test "$CONDA_SHLVL" -ne 0 && test $deactivate_count -lt 10
        if conda deactivate 2>/dev/null
            set deactivate_count (math $deactivate_count + 1)
        else
            echo "Warning: failed to deactivate environment, continuing..." 1>&2
            break
        end
    end
end

# does conda install exist?
if not test -f "$_DEVENV/conda-meta/history"
    # set installer-specific values
    switch $_INSTALLER_TYPE
        case miniconda
            set _INSTALLER_FILE "$_INSTALLER/miniconda"
            set _INSTALLER_DISPLAY "miniconda"
            switch $_MACH
                case Darwin
                    set _DOWNLOAD_URL "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-$_ARCH.sh"
                case Linux
                    set _DOWNLOAD_URL "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-$_ARCH.sh"
                case '*'
                    set _DOWNLOAD_URL "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
            end
        case miniforge
            set _INSTALLER_FILE "$_INSTALLER/miniforge"
            set _INSTALLER_DISPLAY "miniforge"
            switch $_MACH
                case Darwin
                    set _DOWNLOAD_URL "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-$_ARCH.sh"
                case Linux
                    set _DOWNLOAD_URL "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-$_ARCH.sh"
                case '*'
                    set _DOWNLOAD_URL "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe"
            end
    end

    # downloading installer
    switch $_MACH
        case Darwin Linux
            set _INSTALLER_FILE "$_INSTALLER_FILE.sh"
        case '*'
            set _INSTALLER_FILE "$_INSTALLER_FILE.exe"
    end

    # Remove zero-byte installer files before download
    if test -f "$_INSTALLER_FILE" && not test -s "$_INSTALLER_FILE"
        echo "Warning: removing empty installer file $_INSTALLER_FILE"
        rm -f "$_INSTALLER_FILE"
    end

    if not test -f "$_INSTALLER_FILE"
        echo "Downloading $_INSTALLER_DISPLAY..."
        if test "$_MACH" = "Darwin" || test "$_MACH" = "Linux"
            curl -L --fail --silent --show-error "$_DOWNLOAD_URL" -o "$_INSTALLER_FILE"
        else
            powershell.exe -Command "Invoke-WebRequest -Uri '$_DOWNLOAD_URL' -OutFile '$_INSTALLER_FILE' | Out-Null"
        end
        if not test $status -eq 0 || not test -s "$_INSTALLER_FILE"
            echo "Error: failed to download $_INSTALLER_DISPLAY (file missing or empty)" 1>&2
            return 1
        end
    end

    # installing conda
    echo "Installing development environment..."
    switch $_MACH
        case Darwin Linux
            bash "$_INSTALLER_FILE" -bfp "$_DEVENV" > /dev/null
        case '*'
            cmd.exe /c "start /wait \"\" \"$_INSTALLER_FILE\" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=$_DEVENV > NUL"
    end
    if not test $status -eq 0
        echo "Error: failed to install development environment" 1>&2
        return 1
    end
end

# create empty env if it doesn't exist
if not test -d "$_ENV"
    echo "Creating $_NAME..."
    if not env PYTHONPATH="" "$_BASEEXE" create --yes --quiet "--prefix=$_ENV" > /dev/null
        echo "Error: failed to create $_NAME" 1>&2
        return 1
    end
end

# check if explicitly updating or if 24 hrs since last update
if updating
    echo "Updating $_NAME..."

    if not env PYTHONPATH="" "$_BASEEXE" update --yes --quiet --all "--prefix=$_ENV" > /dev/null
        echo "Error: failed to update development environment" 1>&2
        return 1
    end

    # set channels based on installer type
    switch $_INSTALLER_TYPE
        case miniconda
            set _CHANNEL_NAME "defaults"
        case miniforge
            set _CHANNEL_NAME "conda-forge"
    end

    set install_args --yes --quiet "--prefix=$_ENV" --override-channels "--channel=$_CHANNEL_NAME" "--file=$_SRC/tests/requirements.txt" "--file=$_SRC/tests/requirements-ci.txt"
    if test "$_MACH" = "Linux"
        set install_args $install_args "--file=$_SRC/tests/requirements-Linux.txt"
    end
    set install_args $install_args "python=$_PYTHON"

    if not env PYTHONPATH="" "$_BASEEXE" install $install_args > /dev/null
        echo "Error: failed to update $_NAME" 1>&2
        return 1
    end

    # update timestamp
    touch "$_UPDATED"
end

# "install" conda
# trick conda into importing from our source code and not from site-packages
if test -z "$PYTHONPATH"
    set -gx PYTHONPATH "$_SRC"
else
    set -gx PYTHONPATH "$_SRC:$PYTHONPATH"
end

# copy latest shell scripts
echo "Update shell scripts..."
if not "$_ENVEXE" init --install > /dev/null
    echo "Error: failed to update shell scripts" 1>&2
    return 1
end

# initialize conda command
echo "Initializing shell integration..."
eval (env CONDA_AUTO_ACTIVATE=0 "$_ENVEXE" shell.fish hook) > /dev/null
if not test $status -eq 0
    echo "Error: failed to initialize shell integration" 1>&2
    return 1
end

# activate env
echo "Activating $_NAME..."
if not conda activate "$_ENV" > /dev/null
    echo "Error: failed to activate $_NAME" 1>&2
    return 1
end

cleanup
functions -e cleanup
functions -e updating
