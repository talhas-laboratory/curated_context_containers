import pytest

from app.models.containers import AddSource
from app.services.jobs import JobValidationError, _derive_modality, _validate_sources


def test_blocked_modality_raises():
    manifest = {"modalities": ["text"]}
    source = AddSource(uri="https://example.com/file.pdf", mime="application/pdf")

    with pytest.raises(JobValidationError) as exc:
        _validate_sources([source], manifest["modalities"], manifest)

    assert exc.value.code == "BLOCKED_MODALITY"


def test_pdf_page_limit_enforced():
    manifest = {"modalities": ["pdf"], "pdf": {"max_pages": 5}}
    source = AddSource(
        uri="file:///tmp/sample.pdf",
        mime="application/pdf",
        meta={"pages": 8},
    )

    with pytest.raises(JobValidationError) as exc:
        _validate_sources([source], manifest["modalities"], manifest)

    assert exc.value.code == "PAYLOAD_TOO_LARGE"


def test_modality_derivation_defaults_to_text():
    source = AddSource(uri="https://example.com/readme.txt")
    assert _derive_modality(source) == "text"
