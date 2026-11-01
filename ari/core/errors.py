"""Explicit failures are preferable to fictitious device results."""


class AriError(Exception):
    """Base exception for ARI domain failures."""


class PhaseUnavailableError(AriError):
    """A requested device capability has no implementation in this phase."""


class SchemaVersionError(AriError):
    """An existing database needs an explicit migration, not automatic rewriting."""
