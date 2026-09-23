"""Plain-dict artifact backed by JSON bytes."""

import json

from raft.artifact import register_artifact
from raft.artifact.artifact import Artifact


class DictArtifact(Artifact):
    """Serialize ``dict`` values to JSON bytes."""

    handles_type = dict
    extension = "json"

    def write_bytes(self, data, metadata=None):
        """Serialize a dict to JSON bytes.

        Parameters
        ----------
        data : dict
        metadata : dict or None
            Ignored -- embedding would require wrapping the JSON in
            ``{_raft_metadata, _raft_data}`` and changing the on-disk shape.
            The ``.manifest.json`` file remains the source of truth.

        Returns
        -------
        bytes
        """
        return json.dumps(data, sort_keys=False, indent=2).encode("utf-8")

    def read_bytes(self, blob):
        """Deserialize JSON bytes to a dict.

        Parameters
        ----------
        blob : bytes

        Returns
        -------
        dict
        """
        return json.loads(blob.decode("utf-8"))


register_artifact(DictArtifact)
