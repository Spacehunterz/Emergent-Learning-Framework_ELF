"""
Python LSP Server configuration for Emergent Learning Framework.
This file configures pylsp (Python Language Server Protocol) to use Pyright for type checking.
"""

def pylsp_settings():
    return {
        # Configure Pyright integration
        "pyright": {
            "enabled": True,
        },
        # Configure Pylint (optional)
        "pylint": {
            "enabled": True,
            "args": ["--rcfile=.pylintrc"],
        },
        # Configure Pycodestyle (PEP 8)
        "pycodestyle": {
            "enabled": True,
            "maxLineLength": 100,
        },
        # Configure Pydocstyle
        "pydocstyle": {
            "enabled": False,
        },
        # Configure Autopep8
        "autopep8": {
            "enabled": True,
        },
        # Configure type checking with mypy
        "pylsp_mypy": {
            "enabled": True,
            "live_mode": True,
            "strict": False,
            "overrides": ["--python-version=3.8"],
        },
    }
