#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os.path
import sys
from pathlib import Path

# expose custom extensions
sys.path.insert(0, os.path.abspath("_extensions"))

# expose source code for import
sys.path.insert(0, os.path.abspath("../.."))

import conda

# -- Project information -----------------------------------------------------

project = conda.__name__
copyright = "2017, Anaconda, Inc"
author = conda.__author__
version = release = conda.__version__

# -- General configuration ------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "autoapi.extension",
    "conda_umls",
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autosummary",
    "sphinx.ext.graphviz",
    "sphinx.ext.ifconfig",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_reredirects",
    "sphinx_sitemap",
    "sphinxarg.ext",
    "sphinxcontrib.plantuml",
    "sphinxcontrib.programoutput",
]

# Leave double dashes as they are in the docs. Don't replace -- with -
smartquotes = False

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False


def skip_log(app, what, name, obj, skip, options):
    if what == "attribute" and name == "log":
        skip = True
    return skip


def setup(sphinx):
    sphinx.connect("autoapi-skip-member", skip_log)


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_style = "css/custom.css"

# The name of an image file (relative to this directory) to use as a favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = "img/conda-logo.png"

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
html_extra_path = [
    # Serving the robots.txt since we want to point to the sitemap.xml file
    "robots.txt",
]

html_js_files = [
    "https://cdn.jsdelivr.net/npm/jspanel4@4.12.0/dist/jspanel.js",
    "https://cdn.jsdelivr.net/npm/jspanel4@4.12.0/dist/extensions/modal/jspanel.modal.js",
    "https://unpkg.com/@panzoom/panzoom@4.4.1/dist/panzoom.min.js",
    "js/panzoom.js",
]

html_css_files = ["https://cdn.jsdelivr.net/npm/jspanel4@4.12.0/dist/jspanel.css"]

# Setting the prod URL of the site here as the base URL.
html_baseurl = f"https://docs.conda.io/projects/{project}/"

html_theme_options = {
    # The maximum depth of the table of contents tree. Set this to -1 to allow
    # unlimited depth.
    "navigation_depth": -1,
}


# -- sphinxcontrib.plantuml ------------------------------------------------

plantuml_output_format = "svg_img"
plantuml_jarfile_path = Path(__file__).parent.parent / "_build" / "plantuml.jar"
plantuml = f"java -Djava.awt.headless=true -jar {plantuml_jarfile_path}"


# -- For sphinx.ext.intersphinx --------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pluggy": ("https://pluggy.readthedocs.io/en/stable/", None),
}


# -- For sphinx_sitemap ----------------------------------------------------

sitemap_locales = [None]
sitemap_url_scheme = "{lang}stable/{link}"


# -- For myst_parser -------------------------------------------------------

myst_heading_anchors = 3
myst_enable_extensions = [
    "amsmath",
    "colon_fence",
    "deflist",
    "dollarmath",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "substitution",
    "tasklist",
]


# -- For autoapi.extension -------------------------------------------------

autoapi_dirs = ["../../conda", "../../conda_env"]
autoapi_root = "dev-guide/api"
# Manually inserted into TOC in dev-guide/api.rst for proper integration into
# folder-view
autoapi_add_toctree_entry = False
autoapi_template_dir = "_templates/autoapi"


# -- For sphinx_reredirects ------------------------------------------------

redirects = {
    # internal redirects
    "admin": "user-guide/configuration/admin-multi-user-install.html",
    "api/api": "../../dev-guide/api/conda/api.html",
    "api/index": "../../dev-guide/api.html",
    "api/python_api": "../../dev-guide/api/conda/cli/python_api.html",
    "api/solver": "../../dev-guide/api/conda/api.html#conda.api.Solver",
    "changelog": "release-notes.html",
    "channels": "user-guide/tasks/manage-channels.html",
    "commands": "commands/index.html",
    "config": "user-guide/configuration/index.html",
    "custom-channels": "user-guide/tasks/create-custom-channels.html",
    "download": "user-guide/install/download.html",
    "env-commands": "commands/index.html",
    "faq": "user-guide/tasks/index.html",
    "general-commands": "commands/index.html",
    "get-started": "user-guide/index.html",
    "help/conda-pip-virtualenv-translator": "../commands/index.html",
    "help/silent": "../user-guide/install/index.html",
    "install/central": "../user-guide/configuration/admin-multi-user-install.html",
    "install/full": "../user-guide/install/index.html",
    "install/quick": "../user-guide/install/index.html",
    "install/sample-condarc": "../user-guide/configuration/sample-condarc.html",
    "install/tab-completion": "../user-guide/configuration/enable-tab-completion.html",
    "installation": "user-guide/install/index.html",
    "intro": "index.html",
    "mro": "user-guide/tasks/use-mro-with-conda.html",
    "py2or3": "user-guide/tasks/manage-python.html",
    "r-with-conda": "user-guide/tasks/use-r-with-conda.html",
    "redirects": "index.html",
    "test-drive": "user-guide/getting-started.html",
    "troubleshooting": "user-guide/troubleshooting.html",
    "using/cheatsheet": "../user-guide/cheatsheet.html",
    "using/envs": "../user-guide/tasks/manage-environments.html",
    "using/index": "../user-guide/tasks/index.html",
    "using/pkgs": "../user-guide/tasks/manage-pkgs.html",
    "using/test-drive": "../user-guide/getting-started.html",
    "using/using": "../user-guide/tasks/manage-conda.html",
    # external redirects
    "travis": "https://github.com/conda-incubator/setup-miniconda",
    "user-guide/tasks/use-conda-with-travis-ci": "https://github.com/conda-incubator/setup-miniconda",
    "user-guide/tasks/use-mro-with-conda": "https://docs.anaconda.com/anaconda/user-guide/tasks/use-r-language",
    "user-guide/tasks/use-r-with-conda": "https://docs.anaconda.com/anaconda/user-guide/tasks/use-r-language",
}
