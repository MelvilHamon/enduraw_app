"""Enduraw Form Tracker backend application package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("enduraw-app")
except PackageNotFoundError:  # pragma: no cover - fallback when not installed
    __version__ = "0.1.0"
