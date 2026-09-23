"""PIL image artifact backed by PNG bytes with embedded tEXt metadata."""

import io

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from raft.artifact import register_artifact
from raft.artifact.artifact import Artifact


class PilImageArtifact(Artifact):
    """Serialize ``PIL.Image.Image`` values to PNG bytes.

    Business-card metadata is embedded as PNG tEXt chunks.
    """

    handles_type = Image.Image
    extension = "png"

    def write_bytes(self, data, metadata=None):
        """Serialize an image to PNG bytes, embedding ``metadata`` as tEXt chunks.

        Parameters
        ----------
        data : PIL.Image.Image
        metadata : dict or None
            Business card; keys and values are stringified.

        Returns
        -------
        bytes
        """
        buf = io.BytesIO()
        pnginfo = None
        if metadata:
            pnginfo = PngInfo()
            for k, v in metadata.items():
                pnginfo.add_text(str(k), str(v))
        data.save(buf, format="PNG", pnginfo=pnginfo)
        return buf.getvalue()

    def read_bytes(self, blob):
        """Deserialize PNG bytes to a PIL image (loaded into memory).

        Parameters
        ----------
        blob : bytes

        Returns
        -------
        PIL.Image.Image
        """
        img = Image.open(io.BytesIO(blob))
        img.load()
        return img


register_artifact(PilImageArtifact)
