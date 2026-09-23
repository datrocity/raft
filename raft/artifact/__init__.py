"""Artifact registry with a module-level default and public register/lookup functions.

The registry itself (``_DEFAULT_REGISTRY``) is private. External code interacts
via ``register_artifact`` and ``get_artifact_for``.
"""

from raft.errors import UnsupportedArtifactType


class _ArtifactRegistry:
    """Maps Python types (and optional format hints) to Artifact classes."""

    def __init__(self):
        self._by_type_and_format = {}

    def register(self, artifact_cls, format=None):
        """Register an Artifact subclass.

        Parameters
        ----------
        artifact_cls : type
            An ``Artifact`` subclass with ``handles_type`` set.
        format : str, optional
            Format hint. If ``None`` (default), registered as the default
            class for the type. Format-specific classes are picked up when
            a caller passes ``format=...`` to ``get_for``.
        """
        t = artifact_cls.handles_type
        types = t if isinstance(t, tuple) else (t,)
        for tp in types:
            self._by_type_and_format[(tp, format)] = artifact_cls

    def get_for(self, data, format=None):
        """Return the Artifact class registered for ``type(data)`` and ``format``."""
        for (tp, fmt), cls in self._by_type_and_format.items():
            if fmt == format and isinstance(data, tp):
                return cls
        if format is not None:
            raise UnsupportedArtifactType(
                f"no artifact class registered for {type(data).__name__} "
                f"with format={format!r}"
            )
        raise UnsupportedArtifactType(
            f"no artifact class registered for {type(data).__name__}"
        )


_DEFAULT_REGISTRY = _ArtifactRegistry()


def register_artifact(artifact_cls, format=None):
    """Register an artifact class in the module-level registry.

    Parameters
    ----------
    artifact_cls : type
        An ``Artifact`` subclass with ``handles_type`` set.
    format : str, optional
        Format hint. See ``_ArtifactRegistry.register``.
    """
    _DEFAULT_REGISTRY.register(artifact_cls, format=format)


def get_artifact_for(data, format=None):
    """Look up the artifact class for ``data``, optionally by ``format`` hint.

    Parameters
    ----------
    data : object
    format : str, optional
        Format name (e.g. ``"csv"``). When omitted, the default class for
        ``type(data)`` is returned.

    Returns
    -------
    type
        The ``Artifact`` subclass registered for the type (and optionally format).

    Raises
    ------
    UnsupportedArtifactType
        If no artifact class matches.
    """
    return _DEFAULT_REGISTRY.get_for(data, format=format)


# Import concrete artifact modules so they call register_artifact on import.
# Kept at the bottom to avoid circular imports.
from raft.artifact import dict_, numpy_, pandas_, pandas_csv, pil_  # noqa: E402, F401
