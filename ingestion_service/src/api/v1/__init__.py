from fastapi import APIRouter

from ingestion_service.src.api.v1.ingest import router as ingest_router

router = APIRouter(prefix="/v1")

router.include_router(ingest_router)
