import pytest

from raft.errors import (
    ArtifactNotFound,
    ExperimentAlreadyExists,
    RaftError,
)


def test_all_errors_are_raft_errors():
    assert issubclass(ExperimentAlreadyExists, RaftError)
    assert issubclass(ArtifactNotFound, RaftError)


def test_raft_error_is_an_exception():
    assert issubclass(RaftError, Exception)


def test_error_carries_message():
    err = ArtifactNotFound("no such artifact: result")
    assert str(err) == "no such artifact: result"

    with pytest.raises(ArtifactNotFound, match="no such artifact"):
        raise err
