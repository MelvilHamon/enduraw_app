"""Exceptions raised by the engine layer.

These are backend-agnostic: both the mock and the live CoachAgent engine raise
the same types so callers (step-8 fusion) can handle failures without knowing
which backend is wired.
"""

from __future__ import annotations


class EngineError(Exception):
    """Base class for every engine-layer failure."""


class EngineConfigError(EngineError):
    """The engine is misconfigured (e.g. live mode without base URL / API key)."""


class EngineAuthError(EngineError):
    """The upstream rejected our credentials (HTTP 401)."""


class EngineBadRequest(EngineError):
    """The request was malformed or rejected by the upstream (HTTP 400 / 4xx)."""


class EngineNotFound(EngineError):
    """The requested resource does not exist (HTTP 404, or no mock snapshot)."""


class EngineUpstreamError(EngineError):
    """The upstream failed after retries (HTTP 5xx exhausted, or timeout)."""
