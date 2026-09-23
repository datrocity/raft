import pytest

from raft.artifact import get_artifact_for, register_artifact
from raft.artifact.artifact import Artifact
from raft.errors import UnsupportedArtifactType


class FakeThing:
    pass


class FakeThingArtifact(Artifact):
    """Test artifact for FakeThing."""

    handles_type = FakeThing
    extension = "fake"

    def write_bytes(self, data, metadata=None):
        return b"fake-bytes"

    def read_bytes(self, blob):
        return FakeThing()


def _cleanup_fake():
    from raft import artifact as art_mod

    keys = [
        k
        for k in art_mod._DEFAULT_REGISTRY._by_type_and_format
        if k[0] is FakeThing
    ]
    for k in keys:
        art_mod._DEFAULT_REGISTRY._by_type_and_format.pop(k, None)


def test_register_and_get_artifact_for():
    register_artifact(FakeThingArtifact)
    try:
        assert get_artifact_for(FakeThing()) is FakeThingArtifact
    finally:
        _cleanup_fake()


def test_unregistered_type_raises():
    with pytest.raises(UnsupportedArtifactType):
        get_artifact_for(42)


def test_format_hint_returns_format_specific_class():
    class FakeCsvArtifact(FakeThingArtifact):
        extension = "fake-csv"

    register_artifact(FakeThingArtifact)
    register_artifact(FakeCsvArtifact, format="csv")
    try:
        assert get_artifact_for(FakeThing()) is FakeThingArtifact
        assert get_artifact_for(FakeThing(), format="csv") is FakeCsvArtifact
    finally:
        _cleanup_fake()


def test_unknown_format_raises():
    register_artifact(FakeThingArtifact)
    try:
        with pytest.raises(UnsupportedArtifactType):
            get_artifact_for(FakeThing(), format="nope")
    finally:
        _cleanup_fake()
