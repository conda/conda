load bats-assert
load base


@test "test import conda has correct version" {
    run python -c "import conda; print(conda.__version__)"
    assert_output $(CONDA_DEFAULT_ENV='' python setup.py --version 2> /dev/null)
    assert_success
}

@test "test conda command has correct version" {
    run conda --version
    assert_output "conda $(CONDA_DEFAULT_ENV='' python setup.py --version 2> /dev/null)"
}

@test "test we have activate and deactivate" {
    run which activate
    assert_success
    run which deactivate
    assert_success
}

# @test "test conda update conda with wrong permissions" {
#     skip "not done yet"
#     chmod -R ugo-w $TEST_ENV
#     ls -al $TEST_ENV
#     ls -al $TEST_ENV
#     conda info
# }
