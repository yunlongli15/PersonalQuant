# -*- coding: utf-8 -*-
"""Domain-specific exceptions for the data infrastructure."""


class PersonalQuantError(Exception):
    """Base error."""


class OfflineModeError(PersonalQuantError):
    """A network operation was attempted in OFFLINE_MODE."""


class InvalidSymbolError(PersonalQuantError, ValueError):
    """Symbol cannot be normalized to the canonical form."""


class NotAvailableError(PersonalQuantError):
    """Requested data exists but is not available (e.g. no such report)."""


class NotAvailableAtTimeError(NotAvailableError):
    """Data was not yet public at the requested as-of date (PIT violation)."""


class ExtractionFailedError(PersonalQuantError):
    """A metric could not be extracted from the document with confidence."""


class FetchError(PersonalQuantError):
    """PDF/metadata fetch failed after retries (network, HTTP, hash mismatch)."""


class ValidationFailedError(PersonalQuantError):
    """A record failed data-quality / sanity validation."""
