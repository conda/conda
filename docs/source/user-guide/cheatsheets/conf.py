#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os.path
import sys
from pathlib import Path

# expose custom extensions
sys.path.insert(0, os.path.abspath("../../_extensions"))

# expose source code for import
sys.path.insert(0, os.path.abspath("../../../.."))

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
    "sphinx_simplepdf",
]

templates_path = ["_templates"]

# Leave double dashes as they are in the docs. Don't replace -- with -
smartquotes = False

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "conda_sphinx_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["../../_static"]

# -- Options for Sphinx-SimplePDF ------------------------------------------

simplepdf_vars = {
    'primary': '#43b049',
    'secondary': '#43b049',
    'primary-opaque': 'rgba(67, 176, 73, 0.7)',
    'white': '#ffffff',
    'links': '#43b049',
}

simplepdf_theme_options = {
    'nocover': 'true',
    'nosidebar': 'true',
}

simplepdf_file_name = "cheatsheet.pdf"

# ---------------------------------------------------------------------------
# For overwriting CSS in sphinx-simplepdf extension
# ---------------------------------------------------------------------------

def setup(app):
    #----Override table and main variables------
    app.add_css_file('styles/sources/custom_pdf_variables.css')
