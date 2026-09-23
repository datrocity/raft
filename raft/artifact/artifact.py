"""Abstract Artifact base class.

Subclasses declare the Python type they handle and a file extension, and
implement bytes-level serialization.
"""

from abc import ABC, abstractmethod


class Artifact(ABC):
    """Base class for artifact serializers.

    Subclasses set two class attributes:

    - ``handles_type``: the Python type (or tuple of types) that this artifact
      class serializes.
    - ``extension``: the on-disk file extension (no leading dot).

    Subclasses implement ``write_bytes`` and ``read_bytes``. The ``metadata``
    kwarg on ``write_bytes`` is an opt-in "business card" that formats
    supporting embed (PNG tEXt chunks, parquet schema metadata) will encode
    inline. Subclasses whose format cannot embed accept the kwarg and ignore
    it. All embedded values are stringified.
    """

    handles_type = None
    extension = ""

    @abstractmethod
    def write_bytes(self, data, metadata=None):
        """Serialize ``data`` to bytes.

        Parameters
        ----------
        data : object
            The value to serialize.
        metadata : dict or None
            Optional small "business card" (project, experiment, artifact,
            version, params-json, git_sha, dirty, created_at, author). Values
            will be stringified before embedding. Subclasses whose on-disk
            format cannot embed metadata accept and ignore this kwarg.
        """

    @abstractmethod
    def read_bytes(self, blob):
        """Deserialize ``blob`` (bytes) back to the original Python object."""
