# src/ingestion_service/api/v1/ingest.py
from uuid import uuid4
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status

from ingestion_service.src.api.v1.models import IngestRequest, IngestResponse
from ingestion_service.src.core.database_session import get_sessionmaker
from ingestion_service.src.core.models import IngestionRequest
from ingestion_service.src.core.pipeline import IngestionPipeline
from ingestion_service.src.core.status_manager import StatusManager

# from ingestion_service.src.core.vectorstore.pgvector_store import PgVectorStore
from ingestion_service.src.core.http_vectorstore import HttpVectorStore
from ingestion_service.src.core.config import get_settings
from shared.embedders.factory import get_embedder
from ingestion_service.src.core.ocr.ocr_factory import get_ocr_engine
from ingestion_service.src.core.extractors.pdf import PDFExtractor

# 🔽 NEW IMPORTS (MS4)
from ingestion_service.src.core.document_graph.builder import DocumentGraphBuilder
from ingestion_service.src.core.chunk_assembly.pdf_chunk_assembler import PDFChunkAssembler

router = APIRouter(tags=["ingestion"])
SessionLocal = get_sessionmaker()


class NoOpValidator:
    """Synchronous no-op validator."""

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

    # vector_store = PgVectorStore(
    #    dsn=settings.DATABASE_URL,
    #    dimension=getattr(embedder, "dimension", 3),
    #    provider=provider,
    # )
    vector_store = HttpVectorStore(  # ✅ Call vector_store_service via HTTP
        base_url=settings.VECTOR_STORE_SERVICE_URL,
        provider=provider,
    )

    return IngestionPipeline(
        validator=NoOpValidator(),
        embedder=embedder,
        vector_store=vector_store,
    )


def _extract_text_from_file(
    file: UploadFile, ocr_provider: Optional[str] = None
) -> str:
    """
    Returns extracted text from a file. Uses OCR if file is an image.
    PDFs are handled separately (MS4 always-on).
    """
    content_type = file.content_type or ""
    filename: str = str(file.filename or "")
    file_bytes = file.file.read()

    if content_type.startswith("image/") or filename.endswith(
        (".png", ".jpg", ".jpeg")
    ):
        ocr_engine = get_ocr_engine(ocr_provider or "tesseract")
        return ocr_engine.extract_text(file_bytes) or ""

    try:
        return file_bytes.decode("utf-8")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to read uploaded text file as UTF-8",
        )


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit content for ingestion (metadata-only)",
)
def ingest_json(request: IngestRequest) -> IngestResponse:
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER
    source_type = request.source_type

    ingestion_id = uuid4()

    with SessionLocal() as session:
        manager = StatusManager(session)
        manager.create_request(
            ingestion_id=ingestion_id,
            source_type=source_type,
            metadata=request.metadata,
        )
        manager.mark_running(ingestion_id)

        pipeline = _build_pipeline(provider)

        try:
            pipeline.run(
                text="placeholder ingestion content",
                ingestion_id=str(ingestion_id),
                source_type=source_type,
                provider=provider,
            )
            manager.mark_completed(ingestion_id)
        except Exception as exc:
            manager.mark_failed(ingestion_id, error=str(exc))
            raise HTTPException(
                status_code=500, detail="Ingestion pipeline failed"
            ) from exc

    return IngestResponse(ingestion_id=ingestion_id, status="accepted")


@router.post(
    "/ingest/file",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit file for ingestion (text, PDF, or image)",
)
def ingest_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(default=None),
) -> IngestResponse:
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER

    # ---- metadata parsing ----
    try:
        parsed_metadata = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON") from exc

    ingestion_id = uuid4()
    ocr_provider = parsed_metadata.get("ocr_provider")

    content_type = file.content_type or ""
    filename: str = str(file.filename or "")

    is_pdf = filename.endswith(".pdf") or content_type == "application/pdf"

    pipeline = _build_pipeline(provider)

    # ------------------------------------------------------------------
    # PDF ingestion (MS4 always-on)
    # ------------------------------------------------------------------
    if is_pdf:
        pdf_extractor = PDFExtractor()
        artifacts = pdf_extractor.extract(
            file_bytes=file.file.read(),
            source_name=filename,
        )

        graph = DocumentGraphBuilder().build(artifacts)
        chunks = PDFChunkAssembler().assemble(graph)

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No extractable text found in uploaded PDF",
            )

        source_type = "file"

        with SessionLocal() as session:
            manager = StatusManager(session)
            manager.create_request(
                ingestion_id=ingestion_id,
                source_type=source_type,
                metadata={**parsed_metadata, "filename": filename},
            )
            manager.mark_running(ingestion_id)

            try:
                # ✅ Use public method instead of private methods
                pipeline.run_with_chunks(
                    chunks=chunks,
                    ingestion_id=str(ingestion_id),
                )

                # embeddings = pipeline._embed(chunks)
                # pipeline._persist(
                #    chunks=chunks,
                #    embeddings=embeddings,
                #    ingestion_id=str(ingestion_id),
                # )
                manager.mark_completed(ingestion_id)
            except Exception as exc:
                manager.mark_failed(ingestion_id, error=str(exc))
                raise HTTPException(
                    status_code=500, detail="PDF ingestion pipeline failed"
                ) from exc

        return IngestResponse(ingestion_id=ingestion_id, status="accepted")

    # ------------------------------------------------------------------
    # Non-PDF ingestion (existing behavior)
    # ------------------------------------------------------------------
    text = _extract_text_from_file(file, ocr_provider)
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="No extractable text found in uploaded file",
        )

    source_type = (
        "image"
        if content_type.startswith("image/")
        or filename.endswith((".png", ".jpg", ".jpeg"))
        else "file"
    )

    with SessionLocal() as session:
        manager = StatusManager(session)
        manager.create_request(
            ingestion_id=ingestion_id,
            source_type=source_type,
            metadata={**parsed_metadata, "filename": filename},
        )
        manager.mark_running(ingestion_id)

        try:
            pipeline.run(
                text=text,
                ingestion_id=str(ingestion_id),
                source_type=source_type,
                provider=provider,
            )
            manager.mark_completed(ingestion_id)
        except Exception as exc:
            manager.mark_failed(ingestion_id, error=str(exc))
            raise HTTPException(
                status_code=500, detail="Ingestion pipeline failed"
            ) from exc

    return IngestResponse(ingestion_id=ingestion_id, status="accepted")


@router.get(
    "/ingest/{ingestion_id}",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ingestion status",
)
def ingest_status(ingestion_id: str) -> IngestResponse:
    from uuid import UUID

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
