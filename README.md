# PS. please also refer to SERVICES summary DOCS\SERVICES\summary.md 2026/01/21
## Project Lineage

This project originated from `RAG-Ingestion-Engine` and represents a
forward-looking evolution toward a service-oriented RAG architecture.

The original repository remains stable and unchanged.


# rag-foundry
# Agentic-Rag-Ingestion/README.md

**Category:** Core Microservice / Data Ingestion Layer
**Purpose:** rag-foundry is the ingestion backbone for the Agentic-RAG-Platform. It is responsible for accepting raw content — including text, documents, PDFs, and images — and transforming it into structured, vectorized representations ready for retrieval-augmented generation (RAG).

---

## **Key Responsibilities**

### 1. Content Ingestion
* Accepts multiple content types via API or optional UI.
* Supports both synchronous (in-memory / test) and persistent (DB-backed) workflows.

### 2. Preprocessing & Chunking
* Splits content into deterministic chunks based on size and overlap.
* Prepares data for embedding and semantic search.

### 3. Embedding Layer
* Abstract embedding interface supports OpenAI, local, or mock embedding providers.
* Produces vector representations of chunks for storage and retrieval.

### 4. Vector Store Integration
* Stores vectors in PostgreSQL with `pgvector`.
* Provides CRUD operations and status tracking for ingested content.

### 5. RAG Orchestration Stubs
* Placeholder logic for retrieval, context assembly, and downstream AI workflows.
* Designed to integrate seamlessly into larger Agentic-RAG pipelines.

### 6. API & UI
* **FastAPI endpoints**:
  * `POST /v1/ingest` — submit content for ingestion
  * `GET /v1/ingest/{id}` — check ingestion status
* Optional Gradio UI for quick uploads and monitoring.

---

## **Original Scope**

* Core text ingestion  ✅
* Thin UI for file/text upload  ✅
* Image & OCR ingestion  ⬜
* Document linking & metadata enrichment  ⬜
* Persistent vector storage  ⬜
* Modular, extendable architecture for platform integration

---

## **Documentation Overview**

All project documentation lives in the [`DOCS/`](./DOCS) folder:

### **Architecture**
* ADRs:
  * [ADR-005: Vector Store No ORM](./DOCS/ARCHITECTURE/adr-005-vector-store-no-orm.md)
  * [ADR-006: OCR Boundaries and Progressive Understanding](./DOCS/ARCHITECTURE/adr-006-ocr-boundaries-and-progressive-understanding.md)
  * [ADR-008: Python Version Lock](./DOCS/ARCHITECTURE/adr-008-python-version-lock.md)
* General architecture notes: [`ARCHITECTURE_NOTES.md`](./DOCS/ARCHITECTURE_NOTES.md)
* Integration expectations: [`INGESTION_INTEGRATION_OVERVIEW.md`](./DOCS/INGESTION_INTEGRATION_OVERVIEW.md)
* Retrieval expectations: [`INGESTION_RETRIEVAL_EXPECTATIONS.md`](./DOCS/INGESTION_RETRIEVAL_EXPECTATIONS.md)

### **Design**
* [Design Principles](./DOCS/DESIGN/DESIGN_PRINCIPLES.md)
* [OCR Architecture](./DOCS/DESIGN/OCR_ARCHITECTURE.md)
* [Ingestion API Contract](./DOCS/DESIGN/INGESTION_API_CONTRACT.md)
* Pipeline stages: [PIPELINE_STAGES.md](./DOCS/DESIGN/PIPELINE_STAGEs.md)
* Schema ownership: [SCHEMA_OWNERSHIP.md](./DOCS/DESIGN/SCHEMA_OWNERSHIP.md)
* UI boundaries: [UI_BOUNDARY.md](./DOCS/DESIGN/UI_BOUNDARY.md)

### **Usage**
* [Ingestion Service Guide](./DOCS/USAGE/INGESTION_SERVICE_GUIDE.md)

### **Development**
* [Testing Strategy](./DOCS/DEVELOPMENT/TESTING_STRATEGY.md)
* [Development Setup](./DOCS/DEVELOPMENT_SETUP.md)

---

## **Code Quality**

The project enforces code quality via pre-commit hooks.

**Setup:**
```bash
uv run pre-commit install
````

**Run all checks manually:**

```bash
pre-commit run --all-files
```

**Checks include:**

* Ruff (linting & formatting)
* Pyright (static typing)
* Whitespace and formatting validation

---

## **Notes**

* This microservice is designed as a **foundation for RAG pipelines** — ingestion, chunking, embedding, and storage are core capabilities.
* All ADRs and architecture documents guide decisions and ensure maintainability.
* Legacy or historical docs are stored in [`DOCS-ARCHIVE/`](./DOCS-ARCHIVE) for reference but are **not actively maintained**.

---

## **Contact / Support**

For questions about the project, check the ADRs, design principles, and the usage guide first.
For further discussion, use GitHub Issues or reach out to the maintainers.

---

## **Acknowledgements**

The development of rag-foundry has been accelerated and guided with the help of several resources:

* Generative AI tools: [ChatGPT](https://chat.openai.com), [Perplexity AI](https://www.perplexity.ai), [Google](https://www.google.com), and [DuckAI](https://duck.ai).
* Online community and documentation resources: [Stack Overflow](https://stackoverflow.com), [Docker Documentation](https://docs.docker.com), [GitHub](https://github.com), [Astral Docs](https://docs.astral.sh), among others.

These resources helped speed up development while enabling adherence to open-source best practices and coding standards wherever possible.
