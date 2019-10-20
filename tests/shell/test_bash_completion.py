import pytest


class TestBashCompletion:
    @pytest.mark.complete("conda")
    def test_1(self, completion):
        assert completion

    @pytest.mark.complete("conda -", require_cmd=True)
    def test_2(self, completion):
        assert completion
        assert completion == ['--help', '--version']
