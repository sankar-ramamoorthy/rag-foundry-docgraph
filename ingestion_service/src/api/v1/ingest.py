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

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
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


def extract_text_from_bytes(
    *,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    ocr_provider: Optional[str],
) -> str:
    if content_type.startswith("image/") or filename.endswith((".png", ".jpg", ".jpeg")):
        ocr_engine = get_ocr_engine(ocr_provider or "tesseract")
        return ocr_engine.extract_text(file_bytes) or ""

    try:
        return file_bytes.decode("utf-8")
    except Exception:
        raise ValueError("Unable to decode file as UTF-8")


# ---------------------------------------------------------------------
# Background ingestion (PURE — no FastAPI objects)
# ---------------------------------------------------------------------
def background_ingest_file(
    *,
    ingestion_id: UUID,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    metadata: dict,
):
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER
    pipeline = _build_pipeline(provider)

    is_pdf = filename.endswith(".pdf") or content_type == "application/pdf"
    ocr_provider = metadata.get("ocr_provider")

    with SessionLocal() as session:
        StatusManager(session).mark_running(ingestion_id)

    try:
        if is_pdf:
            pdf_extractor = PDFExtractor()
            artifacts = pdf_extractor.extract(
                file_bytes=file_bytes,
                source_name=filename,
            )

            graph = DocumentGraphBuilder().build(artifacts)
            chunks = PDFChunkAssembler().assemble(graph)

            if not chunks:
                raise RuntimeError("No extractable text found in uploaded PDF")

            pipeline.run_with_chunks(
                chunks=chunks,
                ingestion_id=str(ingestion_id),
            )

        else:
            text = extract_text_from_bytes(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
                ocr_provider=ocr_provider,
            )

            if not text.strip():
                raise RuntimeError("No extractable text found in uploaded file")

            pipeline.run(
                text=text,
                ingestion_id=str(ingestion_id),
                source_type="file",
                provider=provider,
            )

        with SessionLocal() as session:
            StatusManager(session).mark_completed(ingestion_id)

        # Fire-and-forget summary
        summary_url = f"http://llm-service:8000/v1/summarize/{ingestion_id}"
        try:
            httpx.post(summary_url, timeout=15)
            logger.info(f"✅ Summary task dispatched: {summary_url}")
        except Exception as e:
            logger.warning(f"⚠️ Summary dispatch failed: {e}")

    except Exception as exc:
        with SessionLocal() as session:
            StatusManager(session).mark_failed(ingestion_id, error=str(exc))
        logger.error(f"❌ Background ingestion failed: {ingestion_id} - {exc}")


# ---------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------
@router.post(
    "/ingest/file",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(default=None),
) -> IngestResponse:
    try:
        parsed_metadata = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON") from exc

    ingestion_id = uuid4()

    # 🔑 CRITICAL: materialize bytes BEFORE returning
    file_bytes = file.file.read()
    filename = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"

    with SessionLocal() as session:
        StatusManager(session).create_request(
            ingestion_id=ingestion_id,
            source_type="file",
            metadata=parsed_metadata,
        )

    threading.Thread(
        target=background_ingest_file,
        kwargs={
            "ingestion_id": ingestion_id,
            "file_bytes": file_bytes,
            "filename": filename,
            "content_type": content_type,
            "metadata": parsed_metadata,
        },
        daemon=True,
    ).start()

    return IngestResponse(
        ingestion_id=ingestion_id,
        status="accepted",
    )


@router.get(
    "/ingest/{ingestion_id}",
    response_model=IngestResponse,
)
def ingest_status(ingestion_id: str) -> IngestResponse:
    try:
        ingestion_uuid = UUID(ingestion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingestion ID format")

    with SessionLocal() as session:
        request = (
            session.query(IngestionRequest)
            .filter_by(ingestion_id=ingestion_uuid)
            .first()
        )
        if request is None:
            raise HTTPException(status_code=404, detail="Ingestion ID not found")

        return IngestResponse(
            ingestion_id=request.ingestion_id,
            status=request.status,
        )
