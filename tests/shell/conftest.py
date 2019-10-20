# The following was adapted from the test framework for the bash_completion
# project: https://github.com/scop/bash-completion/

# TODO:
# 1. create fixtures for `fish` and `zsh`

import os
import difflib
import re
import shlex
from typing import Iterable, List, Optional, Union

import pexpect
import pytest


PS1 = "(base) /@"
MAGIC_MARK = "__MaGiC-maRKz!__"


@pytest.fixture(scope="class")
def bash(request) -> pexpect.spawn:

    logfile = None
    if os.environ.get("BASHCOMP_TEST_LOGFILE"):
        logfile = open(os.environ["BASHCOMP_TEST_LOGFILE"], "w")

    testdir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir)
    )
    testenvdir = os.path.abspath(
        os.path.join(testdir, os.pardir, 'devenv')
    )

    env = os.environ.copy()
    env.update(
        dict(
            TESTDIR=testdir,
            TESTENVDIR=testenvdir,
            PS1=PS1,
            INPUTRC="%s/shell/config/inputrc" % testdir,
            TERM="dumb",
            LC_COLLATE="C",  # to match Python's default locale unaware sort
        )
    )

    os.chdir(testdir)

    # Start bash
    bash = pexpect.spawn(
        "%s --norc" % os.environ.get("BASHCOMP_TEST_BASH", "bash"),
        maxread=os.environ.get("BASHCOMP_TEST_PEXPECT_MAXREAD", 20000),
        logfile=logfile,
        cwd=testdir,
        env=env,
        encoding="utf-8",  # TODO? or native or...?
        # FIXME: Tests shouldn't depend on dimensions, but it's dificult to
        # expect robustly enough for Bash to wrap lines anywhere (e.g. inside
        # MAGIC_MARK).  Increase window width to reduce wrapping.
        dimensions=(24, 160),
        # TODO? codec_errors="replace",
    )
    bash.expect_exact(PS1)

    # Load bashrc which loads bash_completion.sh and runs the conda setup
    assert_bash_exec(bash, "source '%s/shell/config/bashrc'" % testdir)

    cmd = 'conda'
    request.cls.cmd = cmd

    # We assume that the `bash_completion` package has been installed on
    # the testing system. The following will fail if not.
    if load_completion_for(bash, cmd):
        before_env = get_env(bash)
        yield bash
        # Not exactly sure why, but some errors leave bash in state where
        # getting the env here would fail and trash our test output. So
        # reset to a good state first (Ctrl+C, expect prompt).
        bash.sendintr()
        bash.expect_exact(PS1)
        diff_env(
            before_env,
            get_env(bash),
            "",
        )
    else:
        pytest.fail("Could not load bash completion for conda")

    # Clean up
    bash.close()
    if logfile:
        logfile.close()


def is_bash_type(bash: pexpect.spawn, cmd: Optional[str]) -> bool:
    if not cmd:
        return False
    typecmd = "type %s &>/dev/null && echo -n 0 || echo -n 1" % cmd
    bash.sendline(typecmd)
    bash.expect_exact(typecmd + "\r\n")
    result = bash.expect_exact(["0", "1"]) == 0
    bash.expect_exact(PS1)
    return result


def load_completion_for(bash: pexpect.spawn, cmd: str) -> bool:
    try:
        # Allow __load_completion to fail so we can test completions
        # that are directly loaded in bash_completion without a separate file.
        assert_bash_exec(bash, "__load_completion %s || :" % cmd)
        assert_bash_exec(bash, "complete -p %s &>/dev/null" % cmd)
    except AssertionError:
        return False
    return True


def assert_bash_exec(
    bash: pexpect.spawn, cmd: str, want_output: bool = False, want_newline=True
) -> str:

    # Send command
    bash.sendline(cmd)
    bash.expect_exact(cmd)

    # Find prompt, output is before it
    bash.expect_exact("%s%s" % ("\r\n" if want_newline else "", PS1))
    output = bash.before

    # Retrieve exit status
    echo = "echo $?"
    bash.sendline(echo)
    got = bash.expect(
        [
            r"^%s\r\n(\d+)\r\n%s" % (re.escape(echo), re.escape(PS1)),
            PS1,
            pexpect.EOF,
            pexpect.TIMEOUT,
        ]
    )
    status = bash.match.group(1) if got == 0 else "unknown"

    assert status == "0", 'Error running "%s": exit status=%s, output="%s"' % (
        cmd,
        status,
        output,
    )
    if output:
        assert want_output, (
            'Unexpected output from "%s": exit status=%s, output="%s"'
            % (cmd, status, output)
        )
    else:
        assert not want_output, (
            'Expected output from "%s": exit status=%s, output="%s"'
            % (cmd, status, output)
        )

    return output


def get_env(bash: pexpect.spawn) -> List[str]:
    return (
        assert_bash_exec(
            bash,
            "{ (set -o posix ; set); declare -F; shopt -p; set -o; }",
            want_output=True,
        )
        .strip()
        .splitlines()
    )


def diff_env(before: List[str], after: List[str], ignore: str):
    diff = [
        x
        for x in difflib.unified_diff(before, after, n=0, lineterm="")
        # Remove unified diff markers:
        if not re.search(r"^(---|\+\+\+|@@ )", x)
        # Ignore variables expected to change:
        and not re.search("^[-+](_|PPID|BASH_REMATCH|OLDPWD)=", x)
        # Ignore likely completion functions added by us:
        and not re.search(r"^\+declare -f _.+", x)
        # ...and additional specified things:
        and not re.search(ignore or "^$", x)
    ]
    # For some reason, COMP_WORDBREAKS gets added to the list after
    # saving. Remove its changes, and note that it may take two lines.
    for i in range(0, len(diff)):
        if re.match("^[-+]COMP_WORDBREAKS=", diff[i]):
            if i < len(diff) and not re.match(r"^\+[\w]+=", diff[i + 1]):
                del diff[i + 1]
            del diff[i]
            break
    assert not diff, "Environment should not be modified"


class CompletionResult:
    """
    Class to hold completion results.
    """

    def __init__(self, output: str, items: Optional[Iterable[str]] = None):
        """
        When items are specified, they are used as the base for comparisons
        provided by this class. When not, regular expressions are used instead.
        This is because it is not always possible to unambiguously split a
        completion output string into individual items, for example when the
        items contain whitespace.

        :param output: All completion output as-is.
        :param items: Completions as individual items. Should be specified
            only in cases where the completions are robustly known to be
            exactly the specified ones.
        """
        self.output = output
        self._items = None if items is None else sorted(items)

    def endswith(self, suffix: str) -> bool:
        return self.output.endswith(suffix)

    def __eq__(self, expected: Union[str, Iterable[str]]) -> bool:
        """
        Returns True if completion contains expected items, and no others.

        Defining __eq__ this way is quite ugly, but facilitates concise
        testing code.
        """
        expiter = [expected] if isinstance(expected, str) else expected
        if self._items is not None:
            return self._items == expiter
        return bool(
            re.match(
                r"^\s*" + r"\s+".join(re.escape(x) for x in expiter) + r"\s*$",
                self.output,
            )
        )

    def __contains__(self, item: str) -> bool:
        if self._items is not None:
            return item in self._items
        return bool(
            re.search(r"(^|\s)%s(\s|$)" % re.escape(item), self.output)
        )

    def __iter__(self) -> Iterable[str]:
        """
        Note that iteration over items may not be accurate when items were not
        specified to the constructor, if individual items in the output contain
        whitespace. In those cases, it errs on the side of possibly returning
        more items than there actually are, and intends to never return fewer.
        """
        return iter(
            self._items
            if self._items is not None
            else re.split(r" {2,}|\r\n", self.output.strip())
        )

    def __len__(self) -> int:
        """
        Uses __iter__, see caveat in it. While possibly inaccurate, this is
        good enough for truthiness checks.
        """
        return len(list(iter(self)))

    def __repr__(self) -> str:
        return "<CompletionResult %s>" % list(self)


def assert_complete(
    bash: pexpect.spawn, cmd: str, **kwargs
) -> CompletionResult:
    skipif = kwargs.get("skipif")
    if skipif:
        try:
            assert_bash_exec(bash, skipif)
        except AssertionError:
            pass
        else:
            pytest.skip(skipif)
    xfail = kwargs.get("xfail")
    if xfail:
        try:
            assert_bash_exec(bash, xfail)
        except AssertionError:
            pass
        else:
            pytest.xfail(xfail)
    cwd = kwargs.get("cwd")
    if cwd:
        assert_bash_exec(bash, "cd '%s'" % cwd)
    env_prefix = "_BASHCOMP_TEST_"
    env = kwargs.get("env", {})
    if env:
        # Back up environment and apply new one
        assert_bash_exec(
            bash,
            " ".join('%s%s="$%s"' % (env_prefix, k, k) for k in env.keys()),
        )
        assert_bash_exec(
            bash,
            "export %s" % " ".join("%s=%s" % (k, v) for k, v in env.items()),
        )
    bash.send(cmd + "\t")
    bash.expect_exact(cmd)
    bash.send(MAGIC_MARK)
    got = bash.expect(
        [
            # 0: multiple lines, result in .before
            r"\r\n" + re.escape(PS1 + cmd) + ".*" + MAGIC_MARK,
            # 1: no completion
            r"^" + MAGIC_MARK,
            # 2: on same line, result in .match
            r"^([^\r]+)%s$" % MAGIC_MARK,
            pexpect.EOF,
            pexpect.TIMEOUT,
        ]
    )
    if got == 0:
        output = bash.before
        if output.endswith(MAGIC_MARK):
            output = bash.before[: -len(MAGIC_MARK)]
        result = CompletionResult(output)
    elif got == 2:
        output = bash.match.group(1)
        result = CompletionResult(output, [shlex.split(cmd + output)[-1]])
    else:
        # TODO: warn about EOF/TIMEOUT?
        result = CompletionResult("", [])
    bash.sendintr()
    bash.expect_exact(PS1)
    if env:
        # Restore environment, and clean up backup
        # TODO: Test with declare -p if a var was set, backup only if yes, and
        #       similarly restore only backed up vars. Should remove some need
        #       for ignore_env.
        assert_bash_exec(
            bash,
            "export %s"
            % " ".join('%s="$%s%s"' % (k, env_prefix, k) for k in env.keys()),
        )
        assert_bash_exec(
            bash,
            "unset -v %s"
            % " ".join("%s%s" % (env_prefix, k) for k in env.keys()),
        )
    if cwd:
        assert_bash_exec(bash, "cd - >/dev/null")
    return result


@pytest.fixture
def completion(request, bash: pexpect.spawn) -> CompletionResult:
    marker = request.node.get_closest_marker("complete")
    if not marker:
        return CompletionResult("", [])
    for pre_cmd in marker.kwargs.get("pre_cmds", []):
        assert_bash_exec(bash, pre_cmd)
    cmd = getattr(request.cls, "cmd", None)
    if marker.kwargs.get("require_longopt"):
        # longopt completions require both command presence and that it
        # responds something useful to --help
        if "require_cmd" not in marker.kwargs:
            marker.kwargs["require_cmd"] = True
        if "xfail" not in marker.kwargs:
            marker.kwargs["xfail"] = (
                "! %s --help &>/dev/null || "
                "! %s --help 2>&1 | command grep -qF -- --help"
            ) % ((cmd,) * 2)
    if marker.kwargs.get("require_cmd") and not is_bash_type(bash, cmd):
        pytest.skip("Command not found")
    return assert_complete(bash, marker.args[0], **marker.kwargs)
