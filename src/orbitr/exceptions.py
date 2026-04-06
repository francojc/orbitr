"""orbitr exception hierarchy.

Exit codes:
  1  SourceError   — network or API failure
  2  UsageError    — bad arguments or missing inputs
  3  ConfigError   — missing or invalid configuration
  4  NoResultsError — query returned no results
"""

from __future__ import annotations


class LumenError(Exception):
    """Base exception for all orbitr errors."""

    def __init__(self, message: str, suggestion: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion


class ConfigError(LumenError):
    """Missing or invalid configuration. Exit code 3."""


class UsageError(LumenError):
    """Bad arguments or missing required inputs. Exit code 2."""


class SourceError(LumenError):
    """Network or API failure from a data source. Exit code 1."""


class NoResultsError(LumenError):
    """Query returned no results. Exit code 4."""
