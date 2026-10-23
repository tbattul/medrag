"""Tests for scripts/generate_synthea.py and scripts/validate_synthea.py.

Run from the repo root with `python -m pytest` so `scripts` is importable.
"""

from pathlib import Path

import pytest

from scripts.generate_synthea import build_command, parse_java_major, sha256_of
from scripts.validate_synthea import age_band, validate_bundle


# --- generate_synthea -------------------------------------------------------


@pytest.mark.parametrize(
    "output, expected",
    [
        ('java version "1.8.0_421"', 8),
        ('openjdk version "17.0.20.1" 2026-08-18', 17),
        ('openjdk version "21" 2023-09-19', 21),
    ],
)
def test_parse_java_major(output, expected):
    assert parse_java_major(output) == expected


def test_parse_java_major_rejects_garbage():
    with pytest.raises(ValueError):
        parse_java_major("command not found")


def test_build_command_pins_seeds_and_reference_date():
    cmd = build_command(
        Path("synthea.jar"), Path("/out"), population=10, seed=7,
        reference_date="20260101", state="Utah",
    )  # fmt: skip
    assert cmd[:3] == ["java", "-jar", "synthea.jar"]
    assert cmd[cmd.index("-s") + 1] == "7"
    assert cmd[cmd.index("-cs") + 1] == "7"
    assert cmd[cmd.index("-r") + 1] == "20260101"
    assert cmd[cmd.index("-p") + 1] == "10"
    assert "--exporter.fhir.export=true" in cmd
    assert cmd[-1] == "Utah"  # state is a positional arg and must come last


def test_sha256_of(tmp_path):
    f = tmp_path / "x.txt"
    f.write_bytes(b"abc")
    assert sha256_of(f) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


# --- validate_synthea -------------------------------------------------------


def make_bundle(*resources):
    return {
        "resourceType": "Bundle",
        "entry": [
            {"fullUrl": f"urn:uuid:{i}", "resource": r} for i, r in enumerate(resources)
        ],
    }


PATIENT = {"resourceType": "Patient", "birthDate": "1970-05-01", "gender": "female"}
ENCOUNTER = {"resourceType": "Encounter", "subject": {"reference": "urn:uuid:0"}}


def test_valid_bundle_has_no_errors():
    assert validate_bundle(make_bundle(PATIENT, ENCOUNTER)) == []


def test_not_a_bundle():
    assert validate_bundle({"resourceType": "Patient"}) != []


def test_missing_patient_and_encounter():
    errors = validate_bundle(make_bundle({"resourceType": "Observation"}))
    assert any("exactly 1 Patient" in e for e in errors)
    assert any("missing resource types" in e for e in errors)


def test_dangling_internal_reference():
    bad = {"resourceType": "Encounter", "subject": {"reference": "urn:uuid:999"}}
    errors = validate_bundle(make_bundle(PATIENT, bad))
    assert errors == ["dangling reference urn:uuid:999"]


def test_shared_reference_must_exist_when_shared_keys_given():
    ref = "Organization?identifier=sys|123"
    enc = {"resourceType": "Encounter", "serviceProvider": {"reference": ref}}
    bundle = make_bundle(PATIENT, enc)
    assert validate_bundle(bundle, shared_keys={ref}) == []
    assert validate_bundle(bundle, shared_keys=set()) != []
    assert validate_bundle(bundle, shared_keys=None) == []  # check skipped


@pytest.mark.parametrize(
    "birth, deceased, band",
    [
        ("2010-01-01", None, "0-17"),
        ("1990-01-01", None, "18-44"),
        ("1970-01-02", None, "45-64"),  # turns 56 in 2026
        ("1950-01-01", None, "65+"),
        ("1950-01-01", "1990-06-01T00:00:00Z", "18-44"),  # age at death, not today
    ],
)
def test_age_band(birth, deceased, band):
    patient = {"birthDate": birth}
    if deceased:
        patient["deceasedDateTime"] = deceased
    assert age_band(patient) == band
