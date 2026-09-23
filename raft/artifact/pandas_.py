"""Pandas DataFrame artifact backed by parquet with embedded metadata."""

import io

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from raft.artifact import register_artifact
from raft.artifact.artifact import Artifact


class PandasDataFrameArtifact(Artifact):
    """Serialize ``pandas.DataFrame`` values to parquet bytes.

    Business-card metadata is embedded in the parquet schema metadata.
    """

    handles_type = pd.DataFrame
    extension = "parquet"

    def write_bytes(self, data, metadata=None):
        """Serialize a DataFrame to parquet bytes, embedding ``metadata``.

        Parameters
        ----------
        data : pandas.DataFrame
        metadata : dict or None
            Business card; values are stringified and merged into the parquet
            schema metadata alongside pyarrow's own pandas metadata.

        Returns
        -------
        bytes
        """
        table = pa.Table.from_pandas(data)
        if metadata:
            existing = dict(table.schema.metadata or {})
            for k, v in metadata.items():
                existing[str(k).encode("utf-8")] = str(v).encode("utf-8")
            table = table.replace_schema_metadata(existing)
        buf = pa.BufferOutputStream()
        pq.write_table(table, buf)
        return buf.getvalue().to_pybytes()

    def read_bytes(self, blob):
        """Deserialize parquet bytes to a DataFrame.

        Parameters
        ----------
        blob : bytes

        Returns
        -------
        pandas.DataFrame
        """
        table = pq.read_table(io.BytesIO(blob))
        return table.to_pandas()


register_artifact(PandasDataFrameArtifact)
