# Decision log

One entry per non-obvious choice: what we chose, what else we considered, and why.

## 2026-10-22 — Synthea generation settings

**Decision:** Generate patients with Synthea **v4.0.0** (pinned by SHA-256), seed **42** for both
population and clinicians, reference date **2026-01-01**, **1,000** living patients in
**Massachusetts**, FHIR R4 JSON only. Script: `scripts/generate_synthea.py`.

**Why:**
- *Pinned release, not `master-branch-latest`:* the rolling build changes whenever Synthea
  merges code, which would silently change our patients and break eval comparisons.
- *Pinned reference date:* without `-r`, Synthea simulates up to "today", so ages and dates
  would differ between runs on different days. Verified: two runs with these settings produce
  byte-identical patient bundles.
- *Same seed for `-s` and `-cs`:* `-s` alone fixes the patients but not which clinicians they
  see, and practitioner references end up in our documents.
- *Massachusetts:* Synthea's default and best-tested demographics; geography doesn't matter
  for CMS national coverage policies.
- *FHIR only (no CSV/C-CDA):* one format to parse; FHIR is what real EHR integrations use,
  which is the relevant skill for an FDE role.

**Consequences:** `-p 1000` counts *living* patients; Synthea also exports the people who died
during the simulation, so the output has 1,152 patient bundles (1,000 alive, 152 deceased)
plus 2 shared bundles (hospitals, practitioners). About 4 GB on disk, ~2.5 min to generate.
Synthea's built-in encounter notes (`DocumentReference`) are templated and thin, so criteria
evidence will come from our hand-written synthetic notes.

**Alternatives considered:** CSV export (easier to load into Postgres, but loses FHIR
structure); a smaller population (faster, but too few patients with the relevant conditions:
e.g. only 182 of 1,152 have chronic low back pain).
