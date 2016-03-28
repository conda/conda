load bats-assert
load base

@test "test ! installing accelerate 2.0.2 downgrades numpy and installs mkl-rt concurrent with mkl" {
    setup_env
    run conda install --yes python=3.4.4 numpy=1.10.4
    refute_output_contains "conda:"
    refute_output_contains "conda-env:"
    run conda install --yes accelerate=2.0.2
    refute_output_contains "DOWNGRADED"
    assert_success
}

@test "regression test for #2197: New solver should prefer newer versions" {
    run conda create --dry-run -n $TEST_ENV accelerate python=2.7
    refute_output_contains "accelerate: 1.0"
    assert_success
}
