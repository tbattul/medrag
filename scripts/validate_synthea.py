"""Validate Synthea FHIR output and print a summary of the population.

Usage (from the repo root):
    python3 scripts/validate_synthea.py                     # checks data/synthea/fhir/
    python3 scripts/validate_synthea.py data/synthea-small/fhir

Exits with status 1 if any bundle fails a check, so it can run in CI later.
"""

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = REPO_ROOT / "data" / "synthea" / "fhir"
# Synthea writes two shared bundles (hospitals, practitioners) next to the patient bundles.
SHARED_PREFIXES = ("hospitalInformation", "practitionerInformation")
REQUIRED_TYPES = {"Patient", "Encounter"}
REFERENCE_DATE = date(2026, 1, 1)  # must match --reference-date in generate_synthea.py


def find_references(node) -> list[str]:
    """Collect every `"reference": "..."` string anywhere inside a FHIR resource."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "reference" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(find_references(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(find_references(item))
    return found


def shared_reference_keys(bundle: dict) -> set[str]:
    """Keys like 'Organization?identifier=SYSTEM|VALUE' that patient bundles use to point
    at resources in the shared hospital/practitioner bundles."""
    keys = set()
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        for ident in resource.get("identifier", []):
            keys.add(
                f"{resource.get('resourceType')}?identifier="
                f"{ident.get('system')}|{ident.get('value')}"
            )
    return keys


def validate_bundle(bundle: dict, shared_keys: set[str] | None = None) -> list[str]:
    """Return a list of problems with one patient bundle (empty list = valid)."""
    if bundle.get("resourceType") != "Bundle":
        return [f"resourceType is {bundle.get('resourceType')!r}, expected 'Bundle'"]
    entries = bundle.get("entry") or []
    if not entries:
        return ["bundle has no entries"]

    errors = []
    full_urls = [e.get("fullUrl") for e in entries]
    if len(set(full_urls)) != len(full_urls):
        errors.append("duplicate fullUrl values")

    types = Counter(e.get("resource", {}).get("resourceType") for e in entries)
    if types["Patient"] != 1:
        errors.append(f"expected exactly 1 Patient, found {types['Patient']}")
    missing = REQUIRED_TYPES - set(types)
    if missing:
        errors.append(f"missing resource types: {sorted(missing)}")

    for entry in entries:
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            for field in ("birthDate", "gender"):
                if not resource.get(field):
                    errors.append(f"Patient has no {field}")

    # Every internal reference (urn:uuid:...) must point at an entry in this bundle,
    # otherwise ingestion would create dangling links between chunks.
    known = set(full_urls)
    for entry in entries:
        for ref in find_references(entry.get("resource", {})):
            if ref.startswith("urn:uuid:") and ref not in known:
                errors.append(f"dangling reference {ref}")
            elif "?identifier=" in ref and shared_keys is not None and ref not in shared_keys:
                errors.append(f"reference not found in shared bundles: {ref}")
    return errors


def age_band(patient: dict) -> str:
    born = date.fromisoformat(patient["birthDate"])
    end = REFERENCE_DATE
    if patient.get("deceasedDateTime"):
        end = date.fromisoformat(patient["deceasedDateTime"][:10])
    age = end.year - born.year - ((end.month, end.day) < (born.month, born.day))
    for limit, label in ((18, "0-17"), (45, "18-44"), (65, "45-64")):
        if age < limit:
            return label
    return "65+"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fhir_dir", nargs="?", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()

    files = sorted(args.fhir_dir.glob("*.json"))
    if not files:
        sys.exit(f"No JSON files in {args.fhir_dir}. Run scripts/generate_synthea.py first.")
    shared_files = [f for f in files if f.name.startswith(SHARED_PREFIXES)]
    patient_files = [f for f in files if f not in shared_files]

    shared_keys = set()
    for path in shared_files:
        shared_keys |= shared_reference_keys(json.loads(path.read_text()))

    failures = {}
    resource_counts = Counter()
    genders, bands = Counter(), Counter()
    deceased = 0
    for path in patient_files:
        try:
            bundle = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            failures[path.name] = [f"invalid JSON: {exc}"]
            continue
        errors = validate_bundle(bundle, shared_keys if shared_files else None)
        if errors:
            failures[path.name] = errors
            continue
        resources = [e["resource"] for e in bundle["entry"]]
        resource_counts.update(r["resourceType"] for r in resources)
        patient = next(r for r in resources if r["resourceType"] == "Patient")
        genders[patient["gender"]] += 1
        bands[age_band(patient)] += 1
        deceased += "deceasedDateTime" in patient

    valid = len(patient_files) - len(failures)
    print(f"Patient bundles: {len(patient_files)}  valid: {valid}  failed: {len(failures)}")
    print(f"Shared bundles:  {len(shared_files)}")
    print(f"Alive: {valid - deceased}  deceased: {deceased}")
    print("Gender:", dict(genders))
    print("Age bands (at reference date or death):", dict(sorted(bands.items())))
    print("Resources per type (top 15):")
    for rtype, count in resource_counts.most_common(15):
        print(f"  {rtype:<28}{count:>10,}")

    if failures:
        print("\nFAILURES (first 10 files):")
        for name, errors in list(failures.items())[:10]:
            print(f"  {name}: {errors[:3]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
