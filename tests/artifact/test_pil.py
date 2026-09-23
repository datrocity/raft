import io

import numpy as np
from PIL import Image

from raft.artifact import get_artifact_for
from raft.artifact.pil_ import PilImageArtifact


def test_registered_on_import():
    img = Image.new("RGB", (2, 2), color="red")
    assert get_artifact_for(img) is PilImageArtifact


def test_extension_is_png():
    assert PilImageArtifact.extension == "png"


def test_roundtrip_preserves_pixels():
    art = PilImageArtifact()
    img = Image.fromarray(
        np.array(
            [[[255, 0, 0], [0, 255, 0]], [[0, 0, 255], [255, 255, 0]]], dtype=np.uint8
        ),
        mode="RGB",
    )
    blob = art.write_bytes(img)
    back = art.read_bytes(blob)
    assert list(back.getdata()) == list(img.getdata())


def test_metadata_is_embedded_in_png_text_chunks():
    art = PilImageArtifact()
    img = Image.new("RGB", (2, 2), color="red")
    card = {
        "project": "walker",
        "experiment": "baseline",
        "artifact": "loss_curve",
        "version": "v1",
        "params": '{"lr": 0.01}',
    }
    blob = art.write_bytes(img, metadata=card)
    reopened = Image.open(io.BytesIO(blob))
    for k, v in card.items():
        assert reopened.info.get(k) == v


def test_metadata_none_still_roundtrips():
    art = PilImageArtifact()
    img = Image.new("RGB", (2, 2), color="red")
    blob = art.write_bytes(img, metadata=None)
    back = art.read_bytes(blob)
    assert list(back.getdata()) == list(img.getdata())


# TODO(Pillow 14, ~2027-10): migrate `img.getdata()` above to
# `img.get_flattened_data()`. Currently silenced-only warning.
