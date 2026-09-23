import numpy as np
import numpy.testing as npt

from raft.artifact import get_artifact_for
from raft.artifact.numpy_ import NumpyArrayArtifact


def test_registered_on_import():
    arr = np.array([1, 2, 3])
    assert get_artifact_for(arr) is NumpyArrayArtifact


def test_extension_is_npy():
    assert NumpyArrayArtifact.extension == "npy"


def test_roundtrip_preserves_array():
    art = NumpyArrayArtifact()
    arr = np.arange(12, dtype=np.float64).reshape(3, 4)
    blob = art.write_bytes(arr)
    back = art.read_bytes(blob)
    npt.assert_array_equal(back, arr)
    assert back.dtype == arr.dtype
