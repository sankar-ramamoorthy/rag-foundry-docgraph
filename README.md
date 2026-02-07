# rag-foundry-docgraph

**Project:** Enhanced RAG platform with structured document-graph knowledge modeling.

**Milestone 1:** Project Planning & Architecture

---

## Overview

`rag-foundry-docgraph` is an evolution of `rag-foundry`, introducing **document-first retrieval** and **explicit relationships** between knowledge units. This project focuses on **structure, clarity, and predictable retrieval** rather than agentic behavior.

---

## Goals

* Create a **deterministic retrieval system** for RAG pipelines
* Avoid prompt bloat by **reasoning over document summaries**
* Introduce a **relationship model** connecting documents
* Maintain **full traceability** of ingested knowledge

---

## Milestone 1 Deliverables

| Issue   | Description                 |
| ------- | --------------------------- |
| MS1-IS1 | ADR-001: Document Node      |
| MS1-IS2 | ADR-002: Relationship Model |
| MS1-IS3 | ADR-003: Retrieval Strategy |
| MS1-IS4 | Design ER Diagrams          |
| MS1-IS5 | Initial README Update       |

---

## Architecture

* **Ingestion Requests:** track every ingestion with metadata and timestamps.
* **Document Nodes:** conceptual units representing summaries and document-level metadata.
* **Vectors:** embedded chunks linked to documents.
* **Document Relations:** typed edges connecting documents (e.g., `explains`, `decision_for`).

**ASCII ER diagram** (from MS1-IS5):

```
                   +--------------------+
                   | INGESTION_REQUESTS |
                   +--------------------+
                   | ingestion_id (PK)  |
                   | source_type        |
                   | ingestion_metadata |
                   | status             |
                   | created_at         |
                   | started_at         |
                   | finished_at        |
                   +--------------------+
                             |
                             | 1
                             | produces
                             v
                   +--------------------+
                   |   DOCUMENT_NODE    |
                   +--------------------+
                   | document_id (PK)   |
                   | title              |
                   | summary            |
                   | summary_embedding  |
                   | doc_type           |
                   | source_metadata    |
                   | ingestion_id (FK)  |
                   +--------------------+
                             |
                             | 1
                             | contains
                             v
                   +--------------------+
                   |       VECTORS      |
                   +--------------------+
                   | id (PK)            |
                   | vector             |
                   | chunk_id           |
                   | chunk_index        |
                   | chunk_text         |
                   | chunk_strategy     |
                   | source_metadata    |
                   | provider           |
                   | document_id (FK)   |
                   +--------------------+

        +-----------------------------------+
        |         DOCUMENT_RELATION         |
        +-----------------------------------+
        | id (PK)                           |
        | from_document_id (FK)             |
        | to_document_id (FK)               |
        | relation_type                      |
        +-----------------------------------+
                 ^               ^
                 |               |
                 +---------------+
                 | connects documents
```

---

## Next Steps (Milestone 2)

* Implement **Document Nodes** table (no behavior change)
* Implement **Document Relationships** table
* Update ingestion and retrieval pipelines to use structured retrieval

---

## How to Use

1. Clone the repo:

```bash
git clone https://github.com/sankar-ramamoorthy/rag-foundry-docgraph.git
cd rag-foundry-docgraph
```

2. Install dependencies (example with poetry):

```bash
poetry install
```

3. Start the development environment with Docker:

```bash
docker-compose up
```

4. Run tests:

```bash
pytest
```

---


---

# 📘 `README.md` (End of Milestone 2)

```md
# rag-foundry-docgraph

**Project:** Structured, document-first Retrieval-Augmented Generation (RAG) platform.

This project evolves traditional chunk-based RAG into a **document-centric knowledge system** with explicit structure, traceability, and future graph reasoning support.

---

## Project Philosophy

Most RAG systems optimize for recall first and structure later.

This project does the opposite:

* documents are **first-class objects**
* chunks are **implementation details**
* relationships are **explicit and typed**
* retrieval evolves **predictably**, not heuristically

The result is a system that favors **clarity, debuggability, and long-term correctness**.

---

## Milestones Overview

### ✅ Milestone 1 — Architecture & Design

* Document Node concept
* Relationship model (design only)
* Retrieval strategy definition
* ER diagrams and ADRs

### ✅ Milestone 2 — Persistence & Models (current)

* Database-backed `DocumentNode`
* pgvector-backed `VectorChunk`
* Alembic-managed migrations
* CRUD operations
* Integration testing strategy

⚠️ **Important:**  
Milestone 2 **does not change retrieval behavior**.

---

## Core Concepts

### Ingestion Requests

Tracks every ingestion event and its lifecycle.

* Source metadata
* Timestamps
* Status
* Traceability anchor

---

### Document Nodes

A **DocumentNode** represents a logical document unit produced by ingestion.

It is:

* the **parent** of multiple vector chunks
* the **identity boundary** for a document
* the **anchor point** for future relationships

DocumentNodes do **not** participate in retrieval yet — they exist to structure data correctly.

---

### Vector Chunks

Vector chunks are embedded text fragments stored in `pgvector`.

They:

* are always linked to a DocumentNode
* are used for similarity search
* preserve current retrieval semantics

---

## Database Model (Milestone 2)

### ASCII ER Diagram

```

+------------------------+
| INGESTION_REQUESTS     |
+------------------------+
| ingestion_id (PK)      |
| source_type            |
| ingestion_metadata     |
| status                 |
| created_at             |
| started_at             |
| finished_at            |
+------------------------+
|
| 1
| produces
v
+------------------------+
| DOCUMENT_NODES         |
+------------------------+
| document_id (PK)       |
| ingestion_id (FK)      |
| title                  |
| text                   |
| source_metadata (JSON) |
| created_at             |
+------------------------+
|
| 1
| contains
v
+------------------------+
| VECTORS                |
+------------------------+
| id (PK)                |
| vector (pgvector)      |
| chunk_id               |
| chunk_index            |
| chunk_text             |
| chunk_strategy         |
| provider               |
| source_metadata (JSON) |
| document_id (FK)       |
+------------------------+

```

---

## Retrieval Behavior (Unchanged)

Milestone 2 **does not modify retrieval logic**.

Current retrieval flow:

```

Query
→ embedding
→ vector similarity search
→ chunks
→ optional document metadata

```

DocumentNodes exist to enable **future structured retrieval**, not to change current behavior.

---

## Testing Strategy

### Unit Tests (CI)

* ❌ Docker
* ❌ Postgres
* ❌ Ollama
* ✅ Pure unit tests
* ✅ Mocked boundaries
* ✅ Fast and deterministic

### Integration Tests (Local / Dev)

* ✅ Docker
* ✅ Postgres + pgvector
* ✅ Ollama (real embeddings)
* ❌ No mock embedder
* ❌ No synthetic embeddings

Integration tests validate **reality**, not speed.

---

## Status

Milestone 2 is complete.

The system now has:

* correct persistence
* explicit structure
* migration safety
* clear boundaries for future evolution

➡️ Next: **Milestone 3 — Relationship-aware retrieval**

---

## License

MIT
