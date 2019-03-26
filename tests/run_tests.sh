#!/usr/bin/env bash

[[ -z $1 ]] && echo "ERROR :: Usage: run_tests.sh test_dir_or_file log_location <keyword>" && exit 1
[[ -z $2 ]] && echo "ERROR :: Usage: run_tests.sh test_dir_or_file log_location <keyword>" && exit 2
[[ ! -f $1 ]] && [[ ! -d $1 ]] && echo "ERROR :: test_dir_or_file must be an existing file or dir" && exit 3
[[ ! -d $2 ]] && echo "ERROR :: log_location must be an existing dir" && exit 4

if [[ $(uname) == Darwin ]]; then
  PF=D
elif [[ $(uname) == Linux ]]; then
  PF=L
else
  PF=W
fi

PYVER=$(python -c "
import os, sys
sys.stdout.write(str(sys.version_info[0]) + '.' +
                 str(sys.version_info[1]) + '.' +
                 str(sys.version_info[2]))
")
echo "PYVER: ${PYVER}"

# .. if pytest-xdist is installed ..?
JOBS="-n=8"
JOBS=

# This stuff exists to make sure hardlinks
# get used and shared VM folders do not
# in *my* dev setup!
if [[ ${PF} == D ]]; then
  _BASETEMP="/opt/conda.tmp.${PYVER}"
elif [[ ${PF} == L ]]; then
# Has stopped working on linux, fails to mkdir this dir
# even though it tried to rm -rf it first. Seems racey
# to be deleting this folder at all.
  _BASETEMP="/opt/conda.tmp.${PYVER}"
  # echo "WARNING :: *Not* using '--basetemp=' on Linux, it is likely that hardlinks will not be used."
else
  _BASETEMP="${HOME}/conda.tmp.${PYVER}"
fi

# For when sharing code between OSes (due to being mounted to different paths)
find . -name '*.pyc' -exec rm {} \;

if [[ -n "${_BASETEMP}" ]]; then
  rm -rf "${_BASETEMP}"
  _BASETEMP="--basetemp=${_BASETEMP}"
fi

set -x
TESTDIR_NO_SLASH=${1////-}
TESTDIR_LOG_FNAME_BIT=${PF}-$(echo ${TESTDIR_NO_SLASH} | sed 's|\.py||g')
KEYWORD=$3
[[ -n ${KEYWORD} ]] && TESTDIR_LOG_FNAME_BIT="${TESTDIR_LOG_FNAME_BIT}-${KEYWORD}"
declare -a _EXTRA_ARGS
if [[ -n ${KEYWORD} ]]; then
  _EXTRA_ARGS+=("-k")
  _EXTRA_ARGS+=("${KEYWORD}")
  TESTDIR_LOG_FNAME_BIT="${TESTDIR_LOG_FNAME_BIT}-${KEYWORD}"
fi
LOG=${2}/${TESTDIR_LOG_FNAME_BIT}-${PYVER}${JOBS//=/-}.$(date +%Y-%m-%d.%H%M%S).log

CONDA_TEST_SAVE_TEMPS=1 \
  pytest \
    ${JOBS} \
    -vvv \
    --durations=0 \
    ${_BASETEMP} \
    "${_EXTRA_ARGS[@]}" \
    ${1} 2>&1 \
  > >(tee -a ${LOG}.stdout) 2> >(tee -a ${LOG}.stderr >&2)
