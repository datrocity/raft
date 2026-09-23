"""Abstract storage backend for raft."""

from abc import ABC, abstractmethod


class Datastore(ABC):
    """Abstract storage backend.

    All paths are strings relative to the datastore root, using forward slashes.
    Implementations must be thread-safe for read but need not be for concurrent write.
    """

    @abstractmethod
    def read(self, path):
        """Read raw bytes at ``path``.

        Parameters
        ----------
        path : str
            Path relative to the datastore root.

        Returns
        -------
        bytes

        Raises
        ------
        KeyError
            If ``path`` does not exist.
        """

    @abstractmethod
    def write(self, path, data):
        """Write raw bytes to ``path``, creating parent directories as needed.

        Overwrites any existing file at ``path``.

        Parameters
        ----------
        path : str
        data : bytes
        """

    @abstractmethod
    def exists(self, path):
        """Return True if ``path`` exists (as file or directory)."""

    @abstractmethod
    def list_dir(self, path):
        """List immediate child names of a directory.

        Raises
        ------
        KeyError
            If ``path`` does not exist or is not a directory. Callers that want
            "empty on missing" should check ``exists`` first or catch the error.
        """

    @abstractmethod
    def makedirs(self, path):
        """Ensure a directory exists at ``path``, including parents."""

    @abstractmethod
    def delete(self, path):
        """Delete a file at ``path``.

        Raises
        ------
        KeyError
            If ``path`` does not exist.
        """
