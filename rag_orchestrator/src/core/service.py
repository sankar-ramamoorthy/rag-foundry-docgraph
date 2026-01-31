# src/core/service.py
import logging
import json
from typing import List, Optional

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

from src.core.config import get_settings
from shared.embedders.query import embed_query
from shared.embedders.factory import get_embedder

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Pydantic response models
# -------------------------------------------------------------------
class RAGResult(BaseModel):
    answer: str
    sources: List[Optional[str]]


class SearchResultItem(BaseModel):
    text: str
    source: Optional[str] = "N/A"


# -------------------------------------------------------------------
# Full RAG pipeline
# -------------------------------------------------------------------
async def run_rag(
    query: str,
    top_k: int = 5,
    provider: str | None = None,
    model: str | None = None,
    timeout_value: int = 60000,
) -> RAGResult:
    """
    Run the full RAG process:
    embed → search → build context → call LLM
    """
    settings = get_settings()
    timeout = httpx.Timeout(timeout_value)

    # Step 1: Embed query
    embedder = get_embedder(
        provider=settings.EMBEDDING_PROVIDER,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        ollama_model=settings.OLLAMA_EMBED_MODEL,
        ollama_batch_size=settings.OLLAMA_BATCH_SIZE,
    )
    embedding = embed_query(query, embedder)
    logger.debug("Query embedding length: %d", len(embedding))

    # Step 2: Search vector store
    search_url = f"{settings.VECTOR_STORE_URL}/v1/vectors/search"
    payload = {"query_vector": embedding, "k": top_k}
    logger.debug(
        "Searching vector store at URL: %s with payload: %s", search_url, payload
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            search_resp = await client.post(search_url, json=payload)
            search_resp.raise_for_status()
            search_results = search_resp.json().get("results", [])
            logger.debug("Search results count: %d", len(search_results))
        except httpx.HTTPStatusError as exc:
            logger.error("Vector store search failed: %s", exc)
            raise HTTPException(status_code=exc.response.status_code, detail=str(exc))
        except httpx.RequestError as exc:
            logger.error("Vector store request error: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    # Step 3: Build LLM context - FIXED: use metadata.chunk_text
    context_parts = []
    for res in search_results:
        try:
            text = res.get("metadata", {}).get("chunk_text", "No text available")
            context_parts.append(text)
        except (KeyError, TypeError) as e:
            logger.warning("Could not parse result: {}", e)  # Fixed line 1
            context_parts.append("No text available")

    context = "\n\n".join(context_parts)
    logger.debug("Built context length: %d chars", len(context))

    # Step 4: Call LLM service
    llm_payload = {"context": context, "query": query}
    params: dict[str, str] = {}
    if provider:
        params["provider"] = provider
    if model:
        params["model"] = model

    llm_url = f"{settings.LLM_SERVICE_URL}/generate"
    logger.debug("Calling LLM service at %s with params=%s", llm_url, params)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            llm_resp = await client.post(llm_url, json=llm_payload, params=params)
            llm_resp.raise_for_status()
            llm_result = llm_resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("LLM service returned HTTP error: %s", exc)
            raise HTTPException(status_code=exc.response.status_code, detail=str(exc))
        except httpx.RequestError as exc:
            logger.error("LLM request failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    # FIXED: Extract sources from metadata
    sources = []
    for res in search_results:
        try:
            source = (
                res.get("metadata", {})
                .get("source_metadata", {})
                .get("source_type", "unknown")
            )
            sources.append(source)
        except (KeyError, TypeError):
            sources.append("unknown")

    return RAGResult(
        answer=llm_result.get("response", ""),
        sources=sources,
    )


# -------------------------------------------------------------------
# Retrieval-only (no LLM)
# -------------------------------------------------------------------
async def search_documents(
    query: str,
    top_k: int = 5,
    timeout_value: int = 3000,
) -> List[SearchResultItem]:
    """
    Search the vector store and return results
    without invoking the LLM.
    """
    settings = get_settings()
    timeout = httpx.Timeout(timeout_value)

    embedder = get_embedder(
        provider=settings.EMBEDDING_PROVIDER,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        ollama_model=settings.OLLAMA_EMBED_MODEL,
        ollama_batch_size=settings.OLLAMA_BATCH_SIZE,
    )
    embedding = embed_query(query, embedder)
    logger.debug("Query embedding length: %d", len(embedding))

    search_url = f"{settings.VECTOR_STORE_URL}/v1/vectors/search"
    payload = {"query_vector": embedding, "k": top_k}
    logger.debug(
        "Searching vector store at URL: %s with payload: %s", search_url, payload
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            search_resp = await client.post(search_url, json=payload)
            search_resp.raise_for_status()
            search_results = search_resp.json().get("results", [])
            logger.debug("Search results count: %d", len(search_results))

            # DEBUG: Log first result structure
            if search_results:
                logger.debug(
                    "First result structure: %s",
                    json.dumps(search_results[0], indent=2),
                )

        except httpx.HTTPStatusError as exc:
            logger.error("Vector store search failed: %s", exc)
            raise HTTPException(status_code=exc.response.status_code, detail=str(exc))
        except httpx.RequestError as exc:
            logger.error("Vector store request error: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    # FIXED: Correctly parse vector store response format
    parsed_results = []
    for res in search_results:
        try:
            text = res.get("metadata", {}).get("chunk_text", "No text available")
            source = (
                res.get("metadata", {})
                .get("source_metadata", {})
                .get("source_type", "unknown")
            )
            parsed_results.append(SearchResultItem(text=text, source=source))
        except (KeyError, TypeError) as e:
            logger.warning("Could not parse result: {}", e)  # Fixed line 1
            parsed_results.append(
                SearchResultItem(text="Parse error", source="unknown")
            )

    return parsed_results
