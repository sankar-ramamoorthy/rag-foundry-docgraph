# src/ingestion_service/api/v1/ingest.py
from uuid import uuid4, UUID
import json
import logging
import threading
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status

from ingestion_service.src.api.v1.models import IngestRequest, IngestResponse
from ingestion_service.src.core.database_session import get_sessionmaker
from ingestion_service.src.core.models import IngestionRequest
from ingestion_service.src.core.pipeline import IngestionPipeline
from ingestion_service.src.core.status_manager import StatusManager
from ingestion_service.src.core.http_vectorstore import HttpVectorStore
from ingestion_service.src.core.config import get_settings
from shared.embedders.factory import get_embedder
from ingestion_service.src.core.ocr.ocr_factory import get_ocr_engine
from ingestion_service.src.core.extractors.pdf import PDFExtractor
from ingestion_service.src.core.document_graph.builder import DocumentGraphBuilder
from ingestion_service.src.core.chunk_assembly.pdf_chunk_assembler import PDFChunkAssembler

SessionLocal = get_sessionmaker()
router = APIRouter(tags=["ingestion"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NoOpValidator:
    def validate(self, text: str) -> None:
        return None

def _build_pipeline(provider: str) -> IngestionPipeline:
    settings = get_settings()
    embedder = get_embedder(
        provider=settings.EMBEDDING_PROVIDER,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        ollama_model=settings.OLLAMA_EMBED_MODEL,
        ollama_batch_size=settings.OLLAMA_BATCH_SIZE,
    )
    vector_store = HttpVectorStore(
        base_url=settings.VECTOR_STORE_SERVICE_URL,
        provider=provider,
    )
    return IngestionPipeline(
        validator=NoOpValidator(),
        embedder=embedder,
        vector_store=vector_store,
    )

def _extract_text_from_file(file: UploadFile, ocr_provider: Optional[str] = None) -> str:
    content_type = file.content_type or ""
    filename: str = str(file.filename or "")
    file_bytes = file.file.read()
    if content_type.startswith("image/") or filename.endswith((".png", ".jpg", ".jpeg")):
        ocr_engine = get_ocr_engine(ocr_provider or "tesseract")
        return ocr_engine.extract_text(file_bytes) or ""
    try:
        return file_bytes.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to read uploaded text file as UTF-8")

# ----------------------------
# Background ingestion
# ----------------------------
def background_ingest_file(ingestion_id: UUID, file: UploadFile, metadata: dict):
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER
    pipeline = _build_pipeline(provider)

    filename: str = str(file.filename or "")
    is_pdf = filename.endswith(".pdf") or (file.content_type or "") == "application/pdf"
    ocr_provider = metadata.get("ocr_provider")

    with SessionLocal() as session:
        manager = StatusManager(session)
        manager.mark_running(ingestion_id)

    try:
        if is_pdf:
            # PDF path
            pdf_extractor = PDFExtractor()
            artifacts = pdf_extractor.extract(file_bytes=file.file.read(), source_name=filename)
            graph = DocumentGraphBuilder().build(artifacts)
            chunks = PDFChunkAssembler().assemble(graph)

            if not chunks:
                raise Exception("No extractable text found in uploaded PDF")

            pipeline.run_with_chunks(chunks=chunks, ingestion_id=str(ingestion_id))

        else:
            # Non-PDF path
            file.file.seek(0)
            text = _extract_text_from_file(file, ocr_provider)
            if not text.strip():
                raise Exception("No extractable text found in uploaded file")
            pipeline.run(text=text, ingestion_id=str(ingestion_id), source_type="file", provider=provider)

        with SessionLocal() as session:
            manager = StatusManager(session)
            manager.mark_completed(ingestion_id)

        # Trigger summary generation (fire-and-forget)
        summary_url = f"http://llm-service:8000/v1/summarize/{ingestion_id}"
        try:
            httpx.post(summary_url, timeout=15)  # 🔹 laptop-friendly timeout
            logger.info(f"✅ Summary task dispatched: {summary_url}")
        except Exception as e:
            logger.warning(f"⚠️ Summary dispatch failed: {summary_url} - {e}")

    except Exception as exc:
        with SessionLocal() as session:
            manager = StatusManager(session)
            manager.mark_failed(ingestion_id, error=str(exc))
        logger.error(f"❌ Background ingestion failed: {ingestion_id} - {exc}")

# ----------------------------
# API endpoints
# ----------------------------
@router.post("/ingest/file", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_file(file: UploadFile = File(...), metadata: Optional[str] = Form(default=None)) -> IngestResponse:
    try:
        parsed_metadata = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON") from exc

    ingestion_id = uuid4()

    with SessionLocal() as session:
        manager = StatusManager(session)
        manager.create_request(ingestion_id=ingestion_id, source_type="file", metadata=parsed_metadata)

    # Fire background ingestion thread
    threading.Thread(target=background_ingest_file, args=(ingestion_id, file, parsed_metadata), daemon=True).start()

    return IngestResponse(ingestion_id=ingestion_id, status="accepted")

@router.get("/ingest/{ingestion_id}", response_model=IngestResponse)
def ingest_status(ingestion_id: str) -> IngestResponse:
    try:
        ingestion_uuid = UUID(ingestion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingestion ID format")

    with SessionLocal() as session:
        request = session.query(IngestionRequest).filter_by(ingestion_id=ingestion_uuid).first()
        if request is None:
            raise HTTPException(status_code=404, detail="Ingestion ID not found")
        return IngestResponse(
            ingestion_id=request.ingestion_id,
            status=request.status,
            created_at=request.created_at,
            started_at=request.started_at,
            finished_at=request.finished_at,
        )
