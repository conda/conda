# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import sys
from logging import getLogger
from pathlib import Path
from subprocess import run

import pytest

from conda.auxlib.ish import dals
from conda.gateways.logging import TokenURLFilter, initialize_logging

log = getLogger(__name__)


TR = TokenURLFilter.TOKEN_REPLACE


def test_token_replace_big_string():
    test_string = dals(
        """
    555.123.4567	+1-(800)-555-2468
    foo@demo.net	bar.ba@test.co.uk
    www.demo.com	http://foo.co.uk/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar
    http://regexr.com/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar
    https://mediatemple.net/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar

      http://132.154.8.8:1010/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar

     /t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar
    /t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar


      https://mediatemple.net/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar

    http://foo.co.uk:8080/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar

    """
    )
    result_string = dals(
        """
    555.123.4567	+1-(800)-555-2468
    foo@demo.net	bar.ba@test.co.uk
    www.demo.com	http://foo.co.uk/t/<TOKEN>/more/stuf/like/this.html?q=bar
    http://regexr.com/t/<TOKEN>/more/stuf/like/this.html?q=bar
    https://mediatemple.net/t/<TOKEN>/more/stuf/like/this.html?q=bar

      http://132.154.8.8:1010/t/<TOKEN>/more/stuf/like/this.html?q=bar

     /t/<TOKEN>/more/stuf/like/this.html?q=bar
    /t/<TOKEN>/more/stuf/like/this.html?q=bar


      https://mediatemple.net/t/<TOKEN>/more/stuf/like/this.html?q=bar

    http://foo.co.uk:8080/t/<TOKEN>/more/stuf/like/this.html?q=bar

    """
    )
    print(TR(test_string))
    assert TR(test_string) == result_string


def test_token_replace_individual_strings():
    assert (
        TR(
            "http://foo.co.uk:8080/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar"
        )
        == "http://foo.co.uk:8080/t/<TOKEN>/more/stuf/like/this.html?q=bar"
    )
    assert (
        TR("     /t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar")
        == "     /t/<TOKEN>/more/stuf/like/this.html?q=bar"
    )
    assert (
        TR("/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar")
        == "/t/<TOKEN>/more/stuf/like/this.html?q=bar"
    )


@pytest.mark.integration
def test_token_not_present_in_conda_create(tmp_path: Path):
    initialize_logging()
    env = os.environ.copy()
    env["CONDA_CHANNELS"] = (
        "https://conda.anaconda.org/t/xx-00000000-0000-0000-0000-000000000000/conda-test"
    )
    p = run(
        [
            sys.executable,
            "-mconda",
            "-vvvv",
            "create",
            "--dry-run",
            "--prefix",
            tmp_path / "env",
            "ca-certificates",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    print(p.stdout)
    print(p.stderr, file=sys.stderr)
    all_output = p.stdout + "\n" + p.stderr
    assert "/t/xx-00000000-0000-0000-0000-000000000000" not in all_output
    assert "/t/<TOKEN>/" in all_output
