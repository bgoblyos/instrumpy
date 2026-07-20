# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
sys.path.insert(0, os.path.abspath('../Devices'))
sys.path.insert(0, os.path.abspath('../Experiments'))

project = 'instrumpy'
copyright = '2026, Bence Göblyös'
author = 'Bence Göblyös'
version = 'v2026-07-20'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',      # Core library for html generation from docstrings
    'sphinx.ext.napoleon',     # Support for NumPy and Google style docstrings
    'sphinx.ext.viewcode',     # Optional: Adds links to your source code
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
autoclass_content = 'both'

autodoc_mock_imports = [
    "Libraries", 
    "libusb",
    "Utilities",
    "Experiments",
    "Devices"
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_css_files = ['custom.css']
html_context = {
    "display_github": True,
    "github_user": "bgoblyos",
    "github_repo": "instrumpy",
    "github_version": "main",
    "conf_py_path": "/Docs/",
}
