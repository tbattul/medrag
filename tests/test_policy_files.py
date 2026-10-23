
import json
from pathlib import Path

from pydantic import ValidationError

from common.schemas import PolicyMetadata


METADATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "policies"
    / "polysomnography"
    / "metadata.json"
)


def test_metadata_is_valid():
    """Check that CMS metadata follows our schema."""

    data = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    metadata = PolicyMetadata.model_validate(data)

    assert metadata.procedure == "polysomnography"
    assert len(metadata.documents) == 2


def test_document_ids_are_unique():
    """Ensure no CMS document is listed twice."""

    data = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    metadata = PolicyMetadata.model_validate(data)

    ids = [doc.doc_id for doc in metadata.documents]

    assert len(ids) == len(set(ids))


def test_invalid_version_is_rejected():
    """A document version cannot be zero or negative."""

    data = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    data["documents"][0]["version"] = -1

    try:
        PolicyMetadata.model_validate(data)
    except ValidationError:
        pass
    else:
        raise AssertionError("A negative version should be rejected")
