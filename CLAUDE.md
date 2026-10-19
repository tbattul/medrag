# CLAUDE.md — project context for Claude Code

Read this first. It records the decisions already made for this project.

## What we're building
**MedRAG — Prior Authorization & Clinical Policy Copilot.** Given a patient and a requested
procedure, the system:
1. retrieves the matching payer coverage policy (CMS NCD/LCD),
2. extracts the policy's criteria as structured JSON,
3. searches the patient record for evidence on each criterion (hybrid search + rerank),
4. labels each criterion met / not met / missing evidence, with citations to source chunks,
5. drafts a prior-auth letter for a human to review.

Purpose: a portfolio project for two people aiming at **Forward Deployed Engineer** and
**data science** roles. It should show messy-data ingestion, agentic RAG, rigorous
evaluation, and deployment trade-offs, not just a chatbot.

## Hard constraints
- **$0 budget. Free tools only.** No AWS, no paid APIs. Don't suggest ECS, Lambda, Bedrock,
  OpenSearch or other paid services unless asked.
- **Synthetic data only** (Synthea, public CMS policies, hand-written synthetic notes).
  Never use or commit real patient data. If MIMIC is ever used, only with local models.
- **LLM layer must stay swappable**: all LLM calls go through `common/llm.py`
  (Ollama / Groq / Gemini, all OpenAI-compatible). Provider is chosen in `.env`.
- Never commit `.env`, API keys, or anything under `data/`.

## Stack
Python 3.11+ with uv · Postgres 16 + pgvector (Docker) for vectors and Postgres full-text
search for BM25-style keyword search · sentence-transformers embeddings
(`BAAI/bge-small-en-v1.5`, 384-dim, must match `db/init.sql`) · LangGraph for the agent ·
FastAPI · Streamlit UI (React later) · RAGAS + a hand-labelled golden set for eval ·
pytest, ruff, pre-commit, GitHub Actions CI.

## Layout
`ingestion/` parsers, chunking, embedding · `retrieval/` hybrid search (vector + full-text,
fused with Reciprocal Rank Fusion), reranking · `agent/` LangGraph flow · `api/` FastAPI ·
`ui/` Streamlit · `eval/` golden set + metric runs · `common/` config, DB, LLM client ·
`db/init.sql` schema (`documents`, `chunks` with `embedding vector(384)` + generated `tsv`) ·
`scripts/` utilities · `docs/` design doc + decision log.

## Commands
```bash
uv sync                          # add --extra ml for embeddings/LangGraph/RAGAS
docker compose up -d db
uv run python scripts/smoke_test.py
uv run uvicorn api.main:app --reload
uv run pytest
uv run ruff check . && uv run ruff format .
```

## How we work
- Two collaborators, one repo in a GitHub org. No direct pushes to `main`.
- Branch per issue: `feat/<issue#>-short-name`; Conventional Commits; small PRs reviewed
  by the other person; squash merge. See CONTRIBUTING.md.
- Every non-obvious choice (model, chunk size, index type, prompt strategy) gets an entry
  in `docs/decisions.md`.
- New code comes with a test. Keep functions small and readable: we must be able to
  explain every line in an interview, so prefer clear code over clever code, and explain
  the reasoning when making design choices.

## Roles
- Member A: data, ingestion, retrieval, evaluation.
- Member B: API, agent, UI, CI.
Both review each other's work and should understand the whole system.

## Plan
| Week | Deliverable |
|---|---|
| 1 | Design doc, both setups working, Synthea data (~1,000 patients), 2–3 CMS policies, ~20 synthetic notes |
| 2–3 | End-to-end basic RAG: ingest → embed → hybrid search → `/search` and `/ask` endpoints, minimal UI |
| 3–4 | LangGraph agent: criteria extraction → per-criterion evidence → judgment → letter |
| 5 | Golden set (~50 cases), retrieval recall@k, criterion accuracy, citation faithfulness, eval in CI |
| 6 | UI polish, demo video, results table in README (local model vs free hosted models: accuracy, latency, cost) |

## Current status
Scaffold done: Docker DB + schema, config, LLM client, FastAPI `/health`, smoke test,
tests, CI, templates. Issues for weeks 1–3 are in `scripts/issues.tsv`.
Next: write `docs/design-doc.md`, generate Synthea data, collect CMS policies.
