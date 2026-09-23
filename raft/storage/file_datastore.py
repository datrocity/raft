"""Local filesystem datastore."""

from pathlib import Path

from raft.storage.datastore import Datastore


class FileDatastore(Datastore):
    """Local filesystem backend.

    Parameters
    ----------
    root : str or pathlib.Path
        Root directory for the datastore. Created if it does not exist.
    """

    def __init__(self, root):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _full(self, path):
        return self._root / path

    def read(self, path):
        """Read bytes at ``path``. See ``Datastore.read``."""
        p = self._full(path)
        if not p.is_file():
            raise KeyError(path)
        return p.read_bytes()

    def write(self, path, data):
        """Write bytes at ``path``. See ``Datastore.write``."""
        p = self._full(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def exists(self, path):
        """Return True if ``path`` exists. See ``Datastore.exists``."""
        return self._full(path).exists()

    def list_dir(self, path):
        """List child names of ``path``. See ``Datastore.list_dir``."""
        p = self._full(path)
        if not p.is_dir():
            raise KeyError(path)
        return sorted(child.name for child in p.iterdir())

    def makedirs(self, path):
        """Ensure directory at ``path`` exists. See ``Datastore.makedirs``."""
        self._full(path).mkdir(parents=True, exist_ok=True)

    def delete(self, path):
        """Delete file at ``path``. See ``Datastore.delete``."""
        p = self._full(path)
        if not p.is_file():
            raise KeyError(path)
        p.unlink()
