#!/usr/bin/env python
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import re
import sys
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from os import makedirs, pathsep
from os.path import abspath, dirname, isdir, join
from shlex import quote
from subprocess import PIPE, STDOUT, Popen, check_output

manpath = join(dirname(__file__), "build", "man")
if not isdir(manpath):
    makedirs(manpath)
rstpath = join(dirname(__file__), "source", "commands")
if not isdir(rstpath):
    makedirs(rstpath)

RST_HEADER = """
.. _{command}_ref:

conda {command}
=======================

.. raw:: html

"""


def run_command(*args, **kwargs):
    include_stderr = kwargs.pop("include_stderr", False)
    if include_stderr:
        stderr_pipe = STDOUT
    else:
        stderr_pipe = PIPE
    p = Popen(*args, stdout=PIPE, stderr=stderr_pipe, **kwargs)
    out, err = p.communicate()
    if err is None:
        err = b""
    out, err = out.decode("utf-8"), err.decode("utf-8")
    if p.returncode != 0:
        print(
            "%r failed with error code %s"
            % (" ".join(map(quote, args[0])), p.returncode),
            file=sys.stderr,
        )
    elif err:
        print("{!r} gave stderr output: {}".format(" ".join(*args), err))

    return out


def str_check_output(*args, **kwargs):
    return check_output(*args, **kwargs).decode("utf-8")


def conda_help(cache=[]):
    if cache:
        return cache[0]
    cache.append(str_check_output(["conda", "--help"]))
    return cache[0]


def conda_command_help(command):
    return str_check_output(["conda"] + command.split() + ["--help"])


def conda_commands():
    print("Getting list of core commands")
    help = conda_help()
    commands = []
    start = False
    for line in help.splitlines():
        # Commands start after "command" header
        if line.strip() == "command":
            start = True
            continue
        if start:
            # The end of the commands
            if not line:
                break
            if line[4] != " ":
                commands.append(line.split()[0])
    return commands


def external_commands():
    print("Getting list of external commands")
    help = conda_help()
    commands = []
    start = False
    for line in help.splitlines():
        # Commands start after "command" header
        if line.strip() == "other commands:":
            start = True
            continue
        if start:
            # The end of the commands
            if not line:
                break
            if line[4] != " ":
                commands.append(line.split()[0])

    # TODO: Parallelize this
    print("Getting list of external subcommands")
    subcommands_re = re.compile(r"\s*\{(.*)\}\s*")
    # Check for subcommands (like conda skeleton pypi)
    command_help = {}

    def get_help(command):
        command_help[command] = conda_command_help(command)
        print("Checked for subcommand help for %s" % command)

    with ThreadPoolExecutor(len(commands)) as executor:
        # list() is needed for force exceptions to be raised
        list(executor.map(get_help, commands))

    for command in command_help:
        help = command_help[command]
        start = False
        for line in help.splitlines():
            if line.strip() == "positional arguments:":
                start = True
                continue
            if start:
                m = subcommands_re.match(line)
                if m:
                    commands.extend([f"{command} {i}" for i in m.group(1).split(",")])
                break
    return commands


def man_replacements():
    # XXX: We should use conda-api for this, but it's currently annoying to set the
    # root prefix with.
    info = json.loads(str_check_output(["conda", "info", "--json"]))
    # We need to use an ordered dict because the root prefix should be
    # replaced last, since it is typically a substring of the default prefix
    r = OrderedDict(
        [
            (info["default_prefix"], "default prefix"),
            (pathsep.join(info["envs_dirs"]), "envs dirs"),
            # For whatever reason help2man won't italicize these on its own
            # Note these require conda > 3.7.1
            (info["user_rc_path"], r"\fI\,user .condarc path\/\fP"),
            (info["sys_rc_path"], r"\fI\,system .condarc path\/\fP"),
            (info["root_prefix"], r"root prefix"),
        ]
    )

    return r


def generate_man(command):
    conda_version = run_command(["conda", "--version"], include_stderr=True)

    manpage = ""
    retries = 5
    while not manpage and retries:
        manpage = run_command(
            [
                "help2man",
                "--name",
                "conda",
                command,
                "--section",
                "1",
                "--source",
                "Anaconda, Inc.",
                "--version-string",
                conda_version,
                "--no-info",
                "conda",
                "command",
            ]
        )
        retries -= 1

    if not manpage:
        sys.exit("Error: Could not get help for conda %s" % command)

    replacements = man_replacements()
    for text in replacements:
        manpage = manpage.replace(text, replacements[text])
    with open(join(manpath, "conda-%s.1" % command.replace(" ", "-")), "w") as f:
        f.write(manpage)

    print("Generated manpage for conda %s" % command)


def generate_html(command):
    command_file = command.replace(" ", "-")

    # Use abspath so that it always has a path separator
    man = Popen(
        ["man", abspath(join(manpath, "conda-%s.1" % command_file))], stdout=PIPE
    )
    htmlpage = check_output(
        [
            "man2html",
            "-bare",  # Don't use HTML, HEAD, or BODY tags
            "title",
            "conda-%s" % command_file,
            "-topm",
            "0",  # No top margin
            "-botm",
            "0",  # No bottom margin
        ],
        stdin=man.stdout,
    )

    with open(join(manpath, "conda-%s.html" % command_file), "wb") as f:
        f.write(htmlpage)
    print("Generated html for conda %s" % command)


def write_rst(command, sep=None):
    command_file = command.replace(" ", "-")
    with open(join(manpath, "conda-%s.html" % command_file)) as f:
        html = f.read()

    rp = rstpath
    if sep:
        rp = join(rp, sep)
    if not isdir(rp):
        makedirs(rp)
    with open(join(rp, "conda-%s.rst" % command_file), "w") as f:
        f.write(RST_HEADER.format(command=command))
        for line in html.splitlines():
            f.write("   ")
            f.write(line)
            f.write("\n")
    print("Generated rst for conda %s" % command)


def main():
    core_commands = conda_commands()

    # let's just hard-code this for now
    # build_commands = ()
    build_commands = [
        "build",
        "convert",
        "develop",
        "index",
        "inspect",
        "inspect channels",
        "inspect linkages",
        "inspect objects",
        "metapackage",
        # 'pipbuild',
        "render",
        # let's drop this one; I've dropped support for it in 4.3.x
        # coming back with TUF in the near future
        # 'sign',
        "skeleton",
        "skeleton cpan",
        "skeleton cran",
        "skeleton luarocks",
        "skeleton pypi",
        "env",
        "env attach",
        "env create",
        "env export",
        "env list",
        "env remove",
        "env update",
        "env upload",
    ]

    commands = sys.argv[1:] or core_commands + build_commands

    def gen_command(command):
        generate_man(command)
        generate_html(command)

    with ThreadPoolExecutor(10) as executor:
        # list() is needed to force exceptions to be raised
        list(executor.map(gen_command, commands))

    for command in [c for c in core_commands if c in commands]:
        write_rst(command)
    for command in [c for c in build_commands if c in commands]:
        if "env" in command:
            write_rst(command, sep="env")
        else:
            write_rst(command, sep="build")


if __name__ == "__main__":
    sys.exit(main())
