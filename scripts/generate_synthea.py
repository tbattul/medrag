"""Generate a reproducible synthetic patient population with Synthea (FHIR R4 JSON).

Usage (from the repo root):
    python3 scripts/generate_synthea.py                 # 1,000 patients -> data/synthea/fhir/
    python3 scripts/generate_synthea.py -p 10 --out data/synthea-small

Same Synthea version + seeds + reference date => the same patients on any machine.
Only the Python standard library is used, so this runs before `uv sync`.
"""

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# Pinned release. To upgrade: change both values (digest is shown on the GitHub release page)
# and log the change in docs/decisions.md, because it changes the generated patients.
SYNTHEA_VERSION = "v4.0.0"
SYNTHEA_SHA256 = "ed43c20ad40ba5c3bc724503a5af032715fe3c491620b766148e7c2361e6ecc1"
SYNTHEA_URL = (
    "https://github.com/synthetichealth/synthea/releases/download/"
    f"{SYNTHEA_VERSION}/synthea-with-dependencies.jar"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
JAR_PATH = REPO_ROOT / ".cache" / "synthea" / f"synthea-{SYNTHEA_VERSION}.jar"
MIN_JAVA_MAJOR = 17


def sha256_of(path: Path) -> str:
    """Hash the file in 1 MB chunks so a 200 MB jar doesn't need to fit in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_jar(jar_path: Path = JAR_PATH) -> Path:
    """Download the pinned Synthea jar once, and always verify its checksum."""
    if not jar_path.exists():
        jar_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading Synthea {SYNTHEA_VERSION} (~200 MB)...")
        tmp_path = jar_path.with_suffix(".part")
        urllib.request.urlretrieve(SYNTHEA_URL, tmp_path)
        tmp_path.rename(jar_path)

    actual = sha256_of(jar_path)
    if actual != SYNTHEA_SHA256:
        sys.exit(
            f"Checksum mismatch for {jar_path}\n  expected {SYNTHEA_SHA256}\n  got      {actual}\n"
            "Delete the file and re-run."
        )
    return jar_path


def parse_java_major(version_output: str) -> int:
    """Read the major version from `java -version` output.

    Java 8 reports '1.8.0_421' (major = 8); Java 9+ reports e.g. '17.0.20.1' (major = 17).
    """
    match = re.search(r'version "(\d+)(?:\.(\d+))?', version_output)
    if not match:
        raise ValueError(f"Could not parse Java version from: {version_output!r}")
    first, second = int(match.group(1)), match.group(2)
    return int(second) if first == 1 and second else first


def check_java() -> None:
    if shutil.which("java") is None:
        sys.exit("Java not found. Install JDK 17+ (see docs/setup notes).")
    # `java -version` prints to stderr, not stdout.
    result = subprocess.run(["java", "-version"], capture_output=True, text=True)
    major = parse_java_major(result.stderr)
    if major < MIN_JAVA_MAJOR:
        sys.exit(f"Synthea needs Java {MIN_JAVA_MAJOR}+, but `java` is Java {major}.")


def build_command(
    jar_path: Path,
    out_dir: Path,
    population: int,
    seed: int,
    reference_date: str,
    state: str,
) -> list[str]:
    """Build the Synthea command line. Kept separate so it's easy to test and read."""
    return [
        "java",
        "-jar",
        str(jar_path),
        "-s", str(seed),             # population seed: which people get generated
        "-cs", str(seed),            # clinician seed: which doctors they see
        "-r", reference_date,        # "today" for the simulation; pinned for reproducibility
        "-p", str(population),       # number of *living* patients (deceased ones are extra)
        f"--exporter.baseDirectory={out_dir}/",
        "--exporter.fhir.export=true",
        "--exporter.csv.export=false",
        "--exporter.ccda.export=false",
        state,
    ]  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-p", "--population", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--reference-date", default="20260101", help="Simulation 'today', YYYYMMDD"
    )
    parser.add_argument("--state", default="Massachusetts")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "synthea")
    parser.add_argument(
        "--overwrite", action="store_true", help="Delete existing output first"
    )
    args = parser.parse_args()

    out_dir = args.out.resolve()
    # Synthea adds files to an existing folder, so an old run would silently mix with the new one.
    if out_dir.exists() and any(out_dir.iterdir()):
        if not args.overwrite:
            sys.exit(f"{out_dir} is not empty. Re-run with --overwrite to replace it.")
        shutil.rmtree(out_dir)

    check_java()
    jar_path = ensure_jar()
    cmd = build_command(
        jar_path,
        out_dir,
        args.population,
        args.seed,
        args.reference_date,
        args.state,
    )
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)
    print(f"Done. FHIR bundles are in {out_dir / 'fhir'}")


if __name__ == "__main__":
    main()
