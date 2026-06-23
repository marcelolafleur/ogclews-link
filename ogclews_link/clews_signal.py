"""DEPRECATED shim. ``cost_of_electricity_ratio`` now lives in ``signals.py`` (it sits beside
the other reform/base price-ratio signals). This module is a re-export only so existing imports
keep working; it is slated for deletion — see the refactor's rm list.
"""
from __future__ import annotations

from .signals import cost_of_electricity_ratio  # noqa: F401
