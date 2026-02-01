---

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

