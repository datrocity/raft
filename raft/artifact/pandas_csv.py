"""Human-readable Pandas artifact backed by CSV with metadata as comment lines.

Opt-in via ``exp.save(df, name, format="csv")``. Default is parquet
(see ``pandas_.py``) which preserves dtypes precisely.
"""

import io

import pandas as pd

from raft.artifact import register_artifact
from raft.artifact.artifact import Artifact

_COMMENT_PREFIX = "# "


class PandasCsvArtifact(Artifact):
    """Serialize a DataFrame to CSV with metadata as ``# key value`` comment lines.

    Trade-off vs the parquet default: CSV is human-readable (``cat result.csv``
    just works) but loses dtypes on the round trip and is slower/larger.
    Use when a scientist genuinely needs to eyeball the file.
    """

    handles_type = pd.DataFrame
    extension = "csv"

    def write_bytes(self, data, metadata=None):
        """Serialize a DataFrame to CSV bytes with optional metadata comments.

        Parameters
        ----------
        data : pandas.DataFrame
        metadata : dict or None
            Business card. Keys and values are stringified into comment lines.

        Returns
        -------
        bytes
        """
        buf = io.StringIO()
        if metadata:
            for k, v in metadata.items():
                buf.write(f"{_COMMENT_PREFIX}{k} {v}\n")
        data.to_csv(buf)
        return buf.getvalue().encode("utf-8")

    def read_bytes(self, blob):
        """Deserialize CSV bytes to a DataFrame, skipping comment lines.

        Parameters
        ----------
        blob : bytes

        Returns
        -------
        pandas.DataFrame
        """
        return pd.read_csv(io.BytesIO(blob), comment="#", index_col=0)


register_artifact(PandasCsvArtifact, format="csv")
