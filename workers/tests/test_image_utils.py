import base64
import io

import pytest

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency guard
    pytest.skip("Pillow not available", allow_module_level=True)

from workers.util.image import load_image_bytes, make_thumbnail


def _make_image_bytes() -> bytes:
    img = Image.new("RGB", (4, 4), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_load_image_bytes_from_base64():
    data = _make_image_bytes()
    encoded = base64.b64encode(data).decode()
    content, mime, filename = load_image_bytes(
        {"meta": {"image_base64": encoded, "mime": "image/png", "filename": "test.png"}}
    )
    assert content.startswith(b"\x89PNG")
    assert mime == "image/png"
    assert filename == "test.png"


def test_make_thumbnail_respects_max_edge():
    data = _make_image_bytes()
    thumb, meta = make_thumbnail(data, max_edge=2, quality=80)
    assert thumb is not None
    assert meta["width"] <= 2
    assert meta["height"] <= 2
