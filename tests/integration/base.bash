setup_env() {
    TEST_ENV='./t_env'
    [[ -d $TEST_ENV ]] && rm -r $TEST_ENV
    conda create -p $TEST_ENV --yes wheel  # just something small to create empty env
    source activate $TEST_ENV
}

teardown_env() {
    source deactivate
    rm -r $TEST_ENV
    unset TEST_ENV
}

teardown() {
    [[ -z "$TEST_ENV" ]] || teardown_env
}
