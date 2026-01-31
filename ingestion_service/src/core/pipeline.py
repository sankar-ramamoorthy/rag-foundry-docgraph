# ingestion_service/src/core/pipeline.py

from __future__ import annotations
from typing import Any, Optional
import logging

from shared.chunks import Chunk
from shared.chunkers.base import BaseChunker
from shared.chunkers.selector import ChunkerFactory

logging.basicConfig(level=logging.DEBUG)


class IngestionPipeline:
    """
    Orchestrates the ingestion pipeline: validate → chunk → embed → persist.

    Two entry points:
    - run(): For text-based ingestion (extracts, chunks, embeds, persists)
    - run_with_chunks(): For pre-chunked content like PDFs (embeds, persists)
    """

    def __init__(
        self,
        *,
        validator,
        chunker: Optional[BaseChunker] = None,
        embedder,
        vector_store,
    ) -> None:
        self._validator = validator
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store

    def run(
        self,
        *,
        text: str,
        ingestion_id: str,
        source_type: str,
        provider: str,
    ) -> None:
        """
        Full pipeline: validate → chunk → embed → persist.

        Use this for simple text ingestion.
        """
        self._validate(text)
        chunks = self._chunk(
            text=text,
            source_type=source_type,
            provider=provider,
        )
        embeddings = self._embed(chunks)
        self._persist(chunks, embeddings, ingestion_id)

    def run_with_chunks(
        self,
        *,
        chunks: list[Chunk],
        ingestion_id: str,
    ) -> None:
        """
        Pipeline for pre-chunked content: embed → persist.

        Use this for PDFs or other content where chunking happened
        upstream (e.g., via PDFChunkAssembler).
        """
        embeddings = self._embed(chunks)
        self._persist(chunks, embeddings, ingestion_id)

    def _validate(self, text: str) -> None:
        """Validate input text (currently no-op)."""
        self._validator.validate(text)

    def _chunk(
        self,
        text: str,
        source_type: str,
        provider: str,
    ) -> list[Chunk]:
        """
        Chunk text using selected strategy.
        Adds metadata to each chunk for provenance.
        """
        if self._chunker is None:
            selected_chunker, chunker_params = ChunkerFactory.choose_strategy(text)
        else:
            selected_chunker = self._chunker
            chunker_params = {}

        chunks: list[Chunk] = selected_chunker.chunk(text, **chunker_params)
        chunk_strategy = getattr(selected_chunker, "chunk_strategy", "unknown")

        # Add provenance metadata to each chunk
        for chunk in chunks:
            chunk.metadata.update(
                {
                    "chunk_strategy": chunk_strategy,
                    "chunker_name": getattr(
                        selected_chunker,
                        "name",
                        selected_chunker.__class__.__name__,
                    ),
                    "chunker_params": dict(chunker_params),
                    "source_type": source_type,
                    "provider": provider,
                }
            )

        return chunks

    def _embed(self, chunks: list[Chunk]) -> list[Any]:
        """
        Generate embeddings for chunks.
        Validates that embedding count matches chunk count.
        """
        embeddings = self._embedder.embed(chunks)

        if len(embeddings) != len(chunks):
            raise ValueError(
                f"Embedder mismatch: {len(chunks)} chunks, {len(embeddings)} embeddings"
            )

        return embeddings

    def _persist(
        self,
        chunks: list[Chunk],
        embeddings: list[Any],
        ingestion_id: str,
    ) -> None:
        """
        Persist chunks and embeddings to vector store.
        """
        self._vector_store.persist(
            chunks=chunks,
            embeddings=embeddings,
            ingestion_id=ingestion_id,
        )
