"""Exception hierarchy for raft.

All raft-raised exceptions inherit from ``RaftError`` so callers can catch
everything from the library with a single ``except``.
"""


class RaftError(Exception):
    """Base class for all raft errors."""


class ExperimentAlreadyExists(RaftError):
    """Raised when an experiment folder exists with different params."""


class ArtifactNotFound(RaftError):
    """Raised when a requested artifact does not exist in the datastore."""


class UnsupportedArtifactType(RaftError):
    """Raised when no registered artifact class can handle the given data type."""
