import sys

win_default_shells = ["cmd.exe", "powershell", "git_bash", "cygwin"]
shells = ["bash", "zsh"]

if sys.platform == "win32":
    shells = win_default_shells

def pytest_addoption(parser):
    parser.addoption("--shell", action="append", default=[],
        help="list of shells to run shell tests on")

def pytest_generate_tests(metafunc):
    if 'shell' in metafunc.fixturenames:
        metafunc.parametrize("shell", metafunc.config.option.shell)
