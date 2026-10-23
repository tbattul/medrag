
# MedRAG — Project Decision Log

### Decision

We selected Polysomnography (sleep study) as the first medical procedure supported by MedRAG.

For the initial prototype, we will focus on evaluating documentation for suspected obstructive sleep apnea (OSA), using applicable Medicare coverage requirements.

### Policy Sources

- Local Coverage Determination: Polysomnography
- LCD ID: L36593
- LCD Version: 37
- Associated Billing and Coding Article: A56995
- Article Version: 15
- Medicare Contractor: Palmetto GBA

### Rationale

- Polysomnography has published Medicare coverage documentation.
- The policy provides clinical requirements that can be converted into structured criteria.
- We can create synthetic patient records to test whether MedRAG retrieves supporting evidence.
- This is a manageable initial use case for our RAG prototype.

### Implementation Decisions

- Downloaded CMS documents will be stored in `data/raw/cms/`.
- Policy metadata will be stored in `policies/polysomnography/metadata.json`.
- Structured coverage criteria will be stored in `policies/polysomnography/criteria.json`.
- Downloaded datasets and policy files will not be committed to Git.
- Policy metadata, criteria, scripts, and tests will be committed to Git.

### Next Actions

1. Verify policy metadata and effective dates.
2. Create the policy metadata JSON file.
3. Define validation schemas.
4. Extract and review the clinical criteria.
5. Implement a reproducible CMS policy download script.
6. Create synthetic clinical notes and evidence labels.
  