from raft.artifact import get_artifact_for
from raft.artifact.dict_ import DictArtifact


def test_registered_on_import():
    assert get_artifact_for({"a": 1}) is DictArtifact


def test_extension_is_json():
    assert DictArtifact.extension == "json"


def test_roundtrip_preserves_dict():
    art = DictArtifact()
    d = {"a": 1, "b": [1, 2, 3], "c": {"nested": True}}
    back = art.read_bytes(art.write_bytes(d))
    assert back == d
