#!/bin/bash -u

TESTLOG="conda-testlog.txt"

echo "rm -rf ~/anaconda/envs/myenv"
rm -rf ~/anaconda/envs/myenv

# Check if TESTLOG exists, removes it

if [[ -f $TESTLOG ]]; then 
    rm $TESTLOG
fi

#Prints the command and error that failed to TESTLOG

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
    "conda envs" 
    "conda create --confirm=no -n myenv sqlite" 
    "conda install --confirm=no -n myenv pandas=0.8.1"
    "conda update --confirm=no -n myenv pandas"
    "conda activate --confirm=no -p ~/anaconda/envs/myenv numba-0.3.1-np17py27_0"
    "conda deactivate --confirm=no -n myenv sqlite-3.7.13-0"
    "conda remove --confirm=no zeromq-2.2.0-0"
    "conda download --confirm=no zeromq-2.2.0-0"
)

for i in "${COND[@]}"; do
    run $i
done