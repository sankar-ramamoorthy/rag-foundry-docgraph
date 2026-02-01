# Project Plan — rag-foundry-docgraph

**Created:** 2026-01-31  

---

## 1. Project Overview

**Purpose:**  
`rag-foundry-docgraph` is an evolution of `rag-foundry`, focused on **document-level knowledge modeling and structured retrieval**. The goal is to improve **deterministic RAG behavior**, reduce **prompt bloat**, and provide **clear, auditable context reasoning**.

**Key Improvements Over `rag-foundry`:**
- Introduce **DocumentNodes** as first-class retrieval units.
- Add **explicit relationships** between documents.
- Implement **structured retrieval plans** instead of flat top-k chunk selection.
- Maintain **deterministic, testable, and debuggable behavior**.
- Keep agent behavior optional or out of scope for now.

---

## 2. Goals & Success Metrics

**Goals:**
1. Implement a **document-level semantic layer** above chunk embeddings.
2. Provide a **graph structure** of relationships between documents.
3. Enable **controlled, predictable context assembly**.
4. Maintain **full compatibility** with existing ingestion pipelines.

**Success Metrics:**
- Each query uses only relevant documents + chunks.
- Prompt length is predictable and bounded.
- Fewer contradictory answers in RAG outputs.
- Every document included in context is traceable to a retrieval rule.
- Clear separation between **conceptual layer** (document summaries) and **evidence layer** (chunks).

---

## 3. Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| M1 | Project planning, documentation, ADRs | In Progress |
| M2 | DocumentNodes table and migrations (no behavior change) | Planned |
| M3 | Document relationships & retrieval plan (graph layer) | Planned |
| M4 | Context assembly logic & testing | Planned |
| M5 | Optional agent integration (future) | Planned |

---

## 4. Dependencies

- **PostgreSQL** with `pgvector` extension.
- **Python 3.11+** (or current version in `rag-foundry`).
- **Docker** / **Docker Compose** for services.
- Python libraries:
  - `sqlalchemy`
  - `alembic`
  - `pytest`
  - `numpy`
  - `faiss` or other vector DB optional
- Optional LLM APIs (Claude, OpenAI, etc.) for validation/testing.

---

## 5. Folder Structure

```text
rag-foundry-docgraph/
├─ docs/                 # Project documentation
│  ├─ PROJECT_PLAN.md    # This file
│  └─ adr/               # Architecture Decision Records
├─ migrations/           # Alembic migrations for Postgres
├─ ingestion_service/    # Ingestion pipeline
├─ llm_service/          # LLM interface
├─ rag_orchestrator/     # RAG orchestration logic
├─ shared/               # Shared utilities
├─ vector_store_service/ # Vector DB interface
├─ tests/                # Unit and integration tests
├─ docker-compose.yml
├─ pyproject.toml
└─ README.md
````

---

## 6. Architecture Decision Records (ADR)

**Proposed ADRs for Milestone 1:**

1. **ADR-001:** Choice of `DocumentNode` as first-class retrieval unit.
2. **ADR-002:** Separation of **document summary embeddings** from **chunk embeddings**.
3. **ADR-003:** Use of **directed, typed relationships** for controlled context expansion.
4. **ADR-004:** Strategy for deterministic, reproducible context assembly.

> ADRs will live in `docs/adr/` and each will have a dedicated markdown file.

---

## 7. Next Steps

1. Review and finalize project plan.
2. Create ADR placeholders in `docs/adr/`.
3. Prepare first migration for `DocumentNodes` table.
4. Start Milestone 2: Document Nodes implementation (no behavior change).


