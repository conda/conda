#!/usr/bin/env bash

[[ -z $1 ]] && echo "ERROR :: Usage: run_tests.sh test_dir_or_file log_location <keyword>" && exit 1
[[ -z $2 ]] && echo "ERROR :: Usage: run_tests.sh test_dir_or_file log_location <keyword>" && exit 2
[[ ! -d $2 ]] && echo "ERROR :: log_location must be an existing dir" && exit 3

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
  _BASETEMP=${HOME}/conda.tmp.${PYVER}
elif [[ ${PF} == L ]]; then
  _BASETEMP=/opt/conda.tmp.${PYVER}
else
  _BASETEMP=${HOME}/conda.tmp.${PYVER}
fi

rm -rf ${_BASETEMP}
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
CONDA_TEST_USER_ENVIRONMENTS_TXT_FILE=/dev/null \
  pytest \
    ${JOBS} \
    -vvv \
    --durations=0 \
    --basetemp=${_BASETEMP} \
    "${_EXTRA_ARGS[@]}" \
    ${1} 2>&1 \
  > >(tee -a ${LOG}.stdout) 2> >(tee -a ${LOG}.stderr >&2)
