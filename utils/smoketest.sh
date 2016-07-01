#!/bin/bash -u

TESTLOG="conda-testlog.txt"

echo "rm -rf ~/anaconda/envs/myenv"
rm -rf ~/anaconda/envs/myenv

if [[ -f $TESTLOG ]]; then 
    rm $TESTLOG
fi

function log()
{
    echo "$*" >> $TESTLOG
}


function run()
{
    echo "-------------------------------------------------------------"
    echo "$*"
    echo "-------------------------------------------------------------"
    echo ""
    eval "$*"
    if [[ $? != 0 ]]; then
        echo ""
        echo "FAILED"
        log "$*"
    else
        echo ""
        echo "PASSED"
    fi
    echo ""
}

declare -a COND=(
    "conda info" 
    "conda list ^m.*lib$" 
    "conda search ^m.*lib$" 
    "conda depends numpy" 
    "conda info -e" 
    "conda create --yes -n myenv sqlite" 
    "conda install --yes -n myenv pandas=0.8.1"
    "conda update --yes -n myenv pandas"
    "conda env --yes -ap ~/anaconda/envs/myenv numba-0.3.1-np17py27_0"
    "conda env --yes -dn myenv sqlite-3.7.13-0"
    "conda local --yes -r zeromq-2.2.0-0"
    "conda local --yes -d zeromq-2.2.0-0"
)

for i in "${COND[@]}"; do
    run $i
done