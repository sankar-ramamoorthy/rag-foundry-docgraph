# ingestion_service/src/core/pipeline.py - MS6 COMPLETE (both run() + run_with_chunks)
from __future__ import annotations
from typing import Any, Optional
import logging
from uuid import uuid4, UUID

from shared.chunks import Chunk
from shared.chunkers.base import BaseChunker
from shared.chunkers.selector import ChunkerFactory
from ingestion_service.src.core.database_session import get_sessionmaker
from ingestion_service.src.core.crud.crud_document_node import create_document_node

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
        Full pipeline: validate → chunk → embed → persist + DocumentNode (MS6).

        Use this for simple text ingestion (TXT files).
        """
        logging.debug(" pipeline.py run() - TEXT PATH - Full MS6 pipeline: validate → chunk → DocumentNode → embed → persist")
        
        # MS6: Create DocumentNode FIRST (before any vectors)
        sessionmaker = get_sessionmaker()
        with sessionmaker() as session:
            document_id = uuid4()
            title = f"{source_type}_document_{ingestion_id[:8]}"  # e.g., "file_document_a1b2c3d4"
            logging.debug(f" MS6 run() Creating DocumentNode: {title} (doc_id={document_id})")
            
            create_document_node(
                session,
                document_id=document_id,
                title=title,
                summary="Document summary pending MS7",
                source=title,
                ingestion_id=UUID(ingestion_id),
                doc_type=source_type,  # "file", "image", etc.
            )
            session.commit()  #  CRITICAL: Commit BEFORE vectors
            logging.debug(f" MS6 run() DocumentNode COMMITTED {document_id} for {ingestion_id}")

        # Continue normal pipeline
        self._validate(text)
        chunks = self._chunk(
            text=text,
            source_type=source_type,
            provider=provider,
        )
        embeddings = self._embed(chunks)
        logging.debug(f" MS6 run() Persisting {len(chunks)} chunks with document_id={document_id}")
        self._persist(chunks, embeddings, ingestion_id, str(document_id))

    def run_with_chunks(
        self,
        *,
        chunks: list[Chunk],
        ingestion_id: str,
    ) -> None:
        """
        Pipeline for pre-chunked content: DocumentNode → embed → persist (MS6).
        Use this for PDFs or other content where chunking happened upstream.
        """
        logging.debug(f" pipeline.py run_with_chunks() - PDF PATH - {len(chunks)} pre-chunked items")
        
        # MS6: Create DocumentNode FIRST
        sessionmaker = get_sessionmaker()
        with sessionmaker() as session:
            document_id = uuid4()
            title = chunks[0].metadata.get("filename", "untitled") if chunks else "untitled"
            logging.debug(f" MS6 run_with_chunks() Creating DocumentNode: {title} (doc_id={document_id})")
            
            create_document_node(
                session,
                document_id=document_id,
                title=title,
                summary="Document summary pending MS7",
                source=title,
                ingestion_id=UUID(ingestion_id),
                doc_type="file",
            )
            session.commit()  # 🔥 CRITICAL: Commit BEFORE vectors
            logging.debug(f" MS6 run_with_chunks() DocumentNode COMMITTED {document_id} for {ingestion_id}")

        # Continue pipeline
        embeddings = self._embed(chunks)
        logging.debug(f" MS6 run_with_chunks() Persisting {len(chunks)} chunks with document_id={document_id}")
        self._persist(chunks, embeddings, ingestion_id, str(document_id))

    def _validate(self, text: str) -> None:
        """Validate input text (currently no-op)."""
        logging.debug(" pipeline.py _validate()")
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
        logging.debug(f" pipeline.py _chunk() text_len={len(text)} source_type={source_type}")
        
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

        logging.debug(f" _chunk() produced {len(chunks)} chunks")
        return chunks

    def _embed(self, chunks: list[Chunk]) -> list[Any]:
        """
        Generate embeddings for chunks.
        Validates that embedding count matches chunk count.
        """
        logging.debug(f" pipeline.py _embed() {len(chunks)} chunks")
        embeddings = self._embedder.embed(chunks)

        if len(embeddings) != len(chunks):
            raise ValueError(
                f"Embedder mismatch: {len(chunks)} chunks, {len(embeddings)} embeddings"
            )

        logging.debug(f" _embed() produced {len(embeddings)} embeddings")
        return embeddings

    def _persist(
        self,
        chunks: list[Chunk],
        embeddings: list[Any],
        ingestion_id: str,
        document_id: str,  # MS6-IS1: Link chunks to DocumentNode
    ) -> None:
        """
        Persist chunks and embeddings to vector store.
        """
        logging.debug(f" pipeline.py _persist() {len(chunks)} chunks doc_id={document_id}")
        self._vector_store.persist(
            chunks=chunks,
            embeddings=embeddings,
            ingestion_id=ingestion_id,
            document_id=document_id,  # MS6-IS1: Pass to vector store
        )
        logging.debug(f" _persist() COMPLETE for doc_id={document_id}")
