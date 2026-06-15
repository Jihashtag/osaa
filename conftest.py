"""Pytest bootstrap for the osaa flat-layout package.

The project is a flat-layout collection of modules that import each other with
bare names (``from models import ...``), so the ``osaa/`` directory itself must
be on ``sys.path``. Adding it here means the whole suite — both the top-level
``test_*.py`` files and those under ``tests/`` — runs the same way regardless of
the current working directory, and every test sees a single, shared instance of
each module (avoiding the dual-import class-identity bug).
"""

import os
import sys

_OSAA_DIR = os.path.dirname(os.path.abspath(__file__))
if _OSAA_DIR not in sys.path:
    sys.path.insert(0, _OSAA_DIR)
