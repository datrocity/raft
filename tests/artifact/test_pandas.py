import io

import pandas as pd
import pandas.testing as pdt
import pyarrow.parquet as pq

from raft.artifact import get_artifact_for
from raft.artifact.pandas_ import PandasDataFrameArtifact
from raft.artifact.pandas_csv import PandasCsvArtifact


def test_registered_on_import():
    df = pd.DataFrame({"a": [1, 2]})
    assert get_artifact_for(df) is PandasDataFrameArtifact


def test_extension_is_parquet():
    assert PandasDataFrameArtifact.extension == "parquet"


def test_roundtrip_preserves_dataframe():
    art = PandasDataFrameArtifact()
    df = pd.DataFrame(
        {"a": [1, 2, 3], "b": ["x", "y", "z"]},
        index=pd.Index([10, 11, 12], name="ix"),
    )
    blob = art.write_bytes(df)
    back = art.read_bytes(blob)
    pdt.assert_frame_equal(back, df)


def test_metadata_is_embedded_in_parquet_schema():
    art = PandasDataFrameArtifact()
    df = pd.DataFrame({"a": [1, 2]})
    card = {
        "project": "walker",
        "experiment": "baseline",
        "artifact": "result",
        "version": "v1",
        "params": '{"lr": 0.01}',
    }
    blob = art.write_bytes(df, metadata=card)
    table = pq.read_table(io.BytesIO(blob))
    md = table.schema.metadata or {}
    decoded = {k.decode(): v.decode() for k, v in md.items()}
    for k, v in card.items():
        assert decoded[k] == v


def test_metadata_none_still_roundtrips():
    art = PandasDataFrameArtifact()
    df = pd.DataFrame({"a": [1, 2]})
    blob = art.write_bytes(df, metadata=None)
    pdt.assert_frame_equal(art.read_bytes(blob), df)


def test_csv_registered_as_format_csv_for_dataframe():
    df = pd.DataFrame({"a": [1, 2]})
    assert get_artifact_for(df, format="csv") is PandasCsvArtifact
    assert get_artifact_for(df) is PandasDataFrameArtifact


def test_csv_extension_is_csv():
    assert PandasCsvArtifact.extension == "csv"


def test_csv_roundtrip_preserves_dataframe():
    art = PandasCsvArtifact()
    df = pd.DataFrame(
        {"a": [1, 2, 3], "b": ["x", "y", "z"]},
        index=pd.Index([10, 11, 12], name="ix"),
    )
    blob = art.write_bytes(df)
    back = art.read_bytes(blob)
    pdt.assert_frame_equal(back, df)


def test_csv_metadata_is_embedded_as_comment_lines():
    art = PandasCsvArtifact()
    df = pd.DataFrame({"a": [1, 2]})
    card = {"project": "walker", "experiment": "baseline", "artifact": "result"}
    blob = art.write_bytes(df, metadata=card)
    head = blob.decode("utf-8").splitlines()
    comment_lines = [ln for ln in head if ln.startswith("#")]
    joined = " ".join(comment_lines)
    for k, v in card.items():
        assert k in joined
        assert v in joined
    back = art.read_bytes(blob)
    pdt.assert_frame_equal(back, df)
