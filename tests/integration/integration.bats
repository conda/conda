load bats-assert

TEST_ENV='./_t_env'

setup() {
    conda create -p $TEST_ENV --copy --yes python
    conda install -p $TEST_ENV --copy --yes --use-local conda=0.0.0
    source activate $TEST_ENV
}

teardown() {
    source deactivate
    rm -r $TEST_ENV
}

@test "test set gives correct conda" {
    run which conda
    assert_output $(pwd)/_t_env/bin/conda
}

@test "test conda update conda with wrong permissions" {
    skip "not done yet"
    chmod -R ugo-w $TEST_ENV
    ls -al $TEST_ENV
    ls -al $TEST_ENV
    conda info
}

