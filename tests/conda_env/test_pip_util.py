# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda_env.pip_util import get_pip_installed_packages

pip_output_attrs = """
Collecting attrs
  Using cached https://files.pythonhosted.org/packages/23/96/d828354fa2dbdf216eaa7b7de0db692f12c234f7ef888cc14980ef40d1d2/attrs-19.1.0-py2.py3-none-any.whl
Installing collected packages: attrs
Successfully installed attrs-19.1.0
"""
pip_output_attrs_expected = ["attrs-19.1.0"]

pip_output_flask = """
Collecting flask
  Using cached https://files.pythonhosted.org/packages/9b/93/628509b8d5dc749656a9641f4caf13540e2cdec85276964ff8f43bbb1d3b/Flask-1.1.1-py2.py3-none-any.whl
Collecting itsdangerous>=0.24 (from flask)
  Using cached https://files.pythonhosted.org/packages/76/ae/44b03b253d6fade317f32c24d100b3b35c2239807046a4c953c7b89fa49e/itsdangerous-1.1.0-py2.py3-none-any.whl
Collecting click>=5.1 (from flask)
  Using cached https://files.pythonhosted.org/packages/fa/37/45185cb5abbc30d7257104c434fe0b07e5a195a6847506c074527aa599ec/Click-7.0-py2.py3-none-any.whl
Collecting Werkzeug>=0.15 (from flask)
  Using cached https://files.pythonhosted.org/packages/b7/61/c0a1adf9ad80db012ed7191af98fa05faa95fa09eceb71bb6fa8b66e6a43/Werkzeug-0.15.6-py2.py3-none-any.whl
Collecting Jinja2>=2.10.1 (from flask)
  Using cached https://files.pythonhosted.org/packages/1d/e7/fd8b501e7a6dfe492a433deb7b9d833d39ca74916fa8bc63dd1a4947a671/Jinja2-2.10.1-py2.py3-none-any.whl
Collecting MarkupSafe>=0.23 (from Jinja2>=2.10.1->flask)
  Using cached https://files.pythonhosted.org/packages/ce/c6/f000f1af136ef74e4a95e33785921c73595c5390403f102e9b231b065b7a/MarkupSafe-1.1.1-cp37-cp37m-macosx_10_6_intel.whl
Installing collected packages: itsdangerous, click, Werkzeug, MarkupSafe, Jinja2, flask
Successfully installed Jinja2-2.10.1 MarkupSafe-1.1.1 Werkzeug-0.15.6 click-7.0 flask-1.1.1 itsdangerous-1.1.0
"""
pip_output_flask_expected = [
    "Jinja2-2.10.1",
    "MarkupSafe-1.1.1",
    "Werkzeug-0.15.6",
    "click-7.0",
    "flask-1.1.1",
    "itsdangerous-1.1.0",
]

pip_output_flask_only = """
Collecting flask
  Using cached https://files.pythonhosted.org/packages/9b/93/628509b8d5dc749656a9641f4caf13540e2cdec85276964ff8f43bbb1d3b/Flask-1.1.1-py2.py3-none-any.whl
Requirement already satisfied: Werkzeug>=0.15 in ./miniconda3/envs/fooo/lib/python3.7/site-packages (from flask) (0.15.6)
Requirement already satisfied: itsdangerous>=0.24 in ./miniconda3/envs/fooo/lib/python3.7/site-packages (from flask) (1.1.0)
Requirement already satisfied: Jinja2>=2.10.1 in ./miniconda3/envs/fooo/lib/python3.7/site-packages (from flask) (2.10.1)
Requirement already satisfied: click>=5.1 in ./miniconda3/envs/fooo/lib/python3.7/site-packages (from flask) (7.0)
Requirement already satisfied: MarkupSafe>=0.23 in ./miniconda3/envs/fooo/lib/python3.7/site-packages (from Jinja2>=2.10.1->flask) (1.1.1)
Installing collected packages: flask
Successfully installed flask-1.1.1
"""
pip_output_flask_only_expected = ["flask-1.1.1"]

pip_output_flask_already_installed = """
Requirement already satisfied: flask in ./miniconda3/envs/fooo/lib/python3.7/site-packages (1.1.1)
Requirement already satisfied: itsdangerous>=0.24 in ./miniconda3/envs/fooo/lib/python3.7/site-packages (from flask) (1.1.0)
Requirement already satisfied: Jinja2>=2.10.1 in ./miniconda3/envs/fooo/lib/python3.7/site-packages (from flask) (2.10.1)
Requirement already satisfied: click>=5.1 in ./miniconda3/envs/fooo/lib/python3.7/site-packages (from flask) (7.0)
Requirement already satisfied: Werkzeug>=0.15 in ./miniconda3/envs/fooo/lib/python3.7/site-packages (from flask) (0.15.6)
Requirement already satisfied: MarkupSafe>=0.23 in ./miniconda3/envs/fooo/lib/python3.7/site-packages (from Jinja2>=2.10.1->flask) (1.1.1)
"""


@pytest.mark.parametrize(
    "pip_output,expected",
    [
        ("Successfully installed foo bar", ["foo", "bar"]),
        (pip_output_attrs, pip_output_attrs_expected),
        (pip_output_flask, pip_output_flask_expected),
        (pip_output_flask_only, pip_output_flask_only_expected),
    ],
)
def test_get_pip_installed_packages(pip_output, expected):
    result = get_pip_installed_packages(pip_output)
    assert result == expected


@pytest.mark.parametrize("pip_output", [pip_output_flask_already_installed, "foo", ""])
def test_get_pip_installed_packages_none(pip_output):
    result = get_pip_installed_packages(pip_output)
    assert result is None
