from conda import utils
from conda.common.path import win_path_to_unix
from .helpers import assert_equals

SOME_PREFIX = "/some/prefix"
SOME_FILES = ["a", "b", "c"]


def test_path_translations():
    paths = [
        (r"z:\miniconda\Scripts\pip.exe",
         "/z/miniconda/Scripts/pip.exe",
         "/cygdrive/z/miniconda/Scripts/pip.exe"),
        (r"z:\miniconda;z:\Documents (x86)\pip.exe;c:\test",
         "/z/miniconda:/z/Documents (x86)/pip.exe:/c/test",
         "/cygdrive/z/miniconda:/cygdrive/z/Documents (x86)/pip.exe:/cygdrive/c/test"),
        # Failures:
        # (r"z:\miniconda\Scripts\pip.exe",
        #  "/z/miniconda/Scripts/pip.exe",
        #  "/cygdrive/z/miniconda/Scripts/pip.exe"),

        # ("z:\\miniconda\\",
        #  "/z/miniconda/",
        #  "/cygdrive/z/miniconda/"),
        ("test dummy text /usr/bin;z:\\documents (x86)\\code\\conda\\tests\\envskhkzts\\test1;z:\\documents\\code\\conda\\tests\\envskhkzts\\test1\\cmd more dummy text",
        "test dummy text /usr/bin:/z/documents (x86)/code/conda/tests/envskhkzts/test1:/z/documents/code/conda/tests/envskhkzts/test1/cmd more dummy text",
        "test dummy text /usr/bin:/cygdrive/z/documents (x86)/code/conda/tests/envskhkzts/test1:/cygdrive/z/documents/code/conda/tests/envskhkzts/test1/cmd more dummy text"),
    ]
    for windows_path, unix_path, cygwin_path in paths:
        assert win_path_to_unix(windows_path) == unix_path
        assert utils.unix_path_to_win(unix_path) == windows_path

        # assert utils.win_path_to_cygwin(windows_path) == cygwin_path
        # assert utils.cygwin_path_to_win(cygwin_path) == windows_path


def test_text_translations():
    test_win_text = "z:\\msarahan\\code\\conda\\tests\\envsk5_b4i\\test 1"
    test_unix_text = "/z/msarahan/code/conda/tests/envsk5_b4i/test 1"
    assert_equals(test_win_text, utils.unix_path_to_win(test_unix_text))
    assert_equals(test_unix_text, win_path_to_unix(test_win_text))

# Some stuff I was playing with, env_unmodified(conda_tests_ctxt_mgmt_def_pol)
# from contextlib import contextmanager
# from conda.base.constants import DEFAULT_CHANNELS
# from conda.base.context import context, reset_context, stack_context_default
# from conda.common.io import env_vars
# from conda.common.compat import odict
# from conda.common.configuration import YamlRawParameter
# from conda.common.serialize import yaml_load
# from conda.models.channel import Channel
# from .test_create import make_temp_prefix
# from os.path import join
# from shutil import rmtree
# is what I ended up with instead.
#
# I do maintain however, that all of:
# env_{var,vars,unmodified} and make_temp_env must be combined into one function
#
# .. because as things stand, they are frequently nested but they can and do
# conflict with each other. For example make_temp_env calls reset_context()
# which will break our ContextStack (which is currently unused, but will be
# later I hope).

# @contextmanager
# def make_default_conda_config(env=dict({})):
#     prefix = make_temp_prefix()
#     condarc = join(prefix, 'condarc')
#     with open(condarc, 'w') as condarcf:
#         condarcf.write("default_channels:\n")
#         for c in list(DEFAULT_CHANNELS):
#             condarcf.write('  - ' + c + '\n')
#     if not env:
#         env2 = dict({'CONDARC': condarc})
#     else:
#         env2 = env.copy()
#         env2['CONDARC'] = condarc
#     with env_vars(env2, lambda: reset_context((condarc,))):
#         try:
#             yield condarc
#         finally:
#             rmtree(prefix, ignore_errors=True)
#             # Expensive and probably unnecessary?
#             reset_context()
#
#
# @contextmanager
# def make_default_conda_config(env=dict({})):
#     with env_vars(env, stack_context_default):
#         reset_context(())
#         rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_load('')))
#         context._set_raw_data(rd)
#         Channel._reset_state()
#         try:
#             yield None
#         finally:
#             pass
#