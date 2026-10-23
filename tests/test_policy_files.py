
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


def test_coverage_rule_references():
    """Every criterion referenced by a rule must exist."""
    import json
    from pathlib import Path

    from common.schemas import Criterion, CoverageRule

    project_root = Path(__file__).resolve().parents[1]
    criteria_path = (
        project_root / "policies" / "polysomnography" / "criteria.json"
    )

    data = json.loads(criteria_path.read_text(encoding="utf-8"))

    criteria = [Criterion.model_validate(c) for c in data["criteria"]]
    rules = [CoverageRule.model_validate(r) for r in data["rules"]]

    criterion_ids = [criterion.id for criterion in criteria]
    assert len(criterion_ids) == len(set(criterion_ids)), (
        "Duplicate criterion IDs found"
    )

    for rule in rules:
        referenced_ids = (
            rule.all_of
            + rule.any_of
            + rule.exclusions
            + rule.exceptions
        )

        for criterion_id in referenced_ids:
            assert criterion_id in criterion_ids, (
                f"Rule {rule.rule_id} references missing criterion "
                f"{criterion_id}"
            )

