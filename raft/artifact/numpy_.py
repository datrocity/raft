"""Numpy array artifact backed by .npy bytes."""

import io

import numpy as np

from raft.artifact import register_artifact
from raft.artifact.artifact import Artifact


class NumpyArrayArtifact(Artifact):
    """Serialize ``numpy.ndarray`` values to .npy bytes."""

    handles_type = np.ndarray
    extension = "npy"

    def write_bytes(self, data, metadata=None):
        """Serialize an ndarray to .npy bytes.

        Parameters
        ----------
        data : numpy.ndarray
        metadata : dict or None
            Ignored -- the .npy format has no place to embed metadata. The
            The ``.manifest.json`` file remains the source of truth.

        Returns
        -------
        bytes
        """
        buf = io.BytesIO()
        np.save(buf, data, allow_pickle=False)
        return buf.getvalue()

    def read_bytes(self, blob):
        """Deserialize .npy bytes to an ndarray.

        Parameters
        ----------
        blob : bytes

        Returns
        -------
        numpy.ndarray
        """
        return np.load(io.BytesIO(blob), allow_pickle=False)


register_artifact(NumpyArrayArtifact)
