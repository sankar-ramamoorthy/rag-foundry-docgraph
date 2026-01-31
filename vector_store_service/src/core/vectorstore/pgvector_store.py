# src/core/vectorstore/pgvector_store.py
from __future__ import annotations
from typing import Sequence, Iterable, List
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
import logging

from src.core.vectorstore.base import (
    VectorStore,
)

from shared.models.vector import (
    VectorRecord,
    VectorMetadata,
)

logging.basicConfig(level=logging.DEBUG)


class PgVectorStore(VectorStore):
    SCHEMA = "ingestion_service"
    TABLE_NAME = "vectors"

    def __init__(self, dsn: str, dimension: int, provider: str = "mock") -> None:
        self._dsn = dsn
        self._dimension = dimension
        self._provider = provider
        self._validate_table()

    @property
    def dimension(self) -> int:
        return self._dimension

    def persist(self, records: list[VectorRecord], ingestion_id: str) -> None:
        """Store vector records - no knowledge of chunks needed."""
        self.add(records)

        logging.debug("PgVectorStore.persist: added %d records", len(records))

    def add(self, records: Iterable[VectorRecord]) -> None:
        insert_sql = sql.SQL(
            """
            INSERT INTO {schema}.{table}
                (vector,
                 ingestion_id,
                 chunk_id,
                 chunk_index,
                 chunk_strategy,
                 chunk_text,
                 source_metadata,
                 provider)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
        ).format(
            schema=sql.Identifier(self.SCHEMA),
            table=sql.Identifier(self.TABLE_NAME),
        )

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                for record in records:
                    cur.execute(
                        insert_sql,
                        (
                            record.vector,
                            record.metadata.ingestion_id,
                            record.metadata.chunk_id,
                            record.metadata.chunk_index,
                            record.metadata.chunk_strategy,
                            record.metadata.chunk_text,
                            Jsonb(record.metadata.source_metadata or {}),
                            record.metadata.provider or self._provider,
                        ),
                    )

    def similarity_search(
        self, query_vector: Sequence[float], k: int
    ) -> List[VectorRecord]:
        search_sql = sql.SQL(
            """
            SELECT
                vector,
                ingestion_id,
                chunk_id,
                chunk_index,
                chunk_strategy,
                chunk_text,
                source_metadata,
                provider
            FROM {schema}.{table}
            ORDER BY vector <-> (%s::vector)
            LIMIT %s
            """
        ).format(
            schema=sql.Identifier(self.SCHEMA),
            table=sql.Identifier(self.TABLE_NAME),
        )

        results: List[VectorRecord] = []

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(search_sql, (query_vector, k))
                for row in cur.fetchall():
                    (
                        vector,
                        ingestion_id,
                        chunk_id,
                        chunk_index,
                        chunk_strategy,
                        chunk_text,
                        source_metadata,
                        provider,
                    ) = row

                    metadata = VectorMetadata(
                        ingestion_id=ingestion_id,
                        chunk_id=chunk_id,
                        chunk_index=chunk_index,
                        chunk_strategy=chunk_strategy,
                        chunk_text=chunk_text,
                        source_metadata=source_metadata,
                        provider=provider,
                    )
                    results.append(VectorRecord(vector=vector, metadata=metadata))

        return results

    def delete_by_ingestion_id(self, ingestion_id: str) -> None:
        delete_sql = sql.SQL(
            """
            DELETE FROM {schema}.{table}
            WHERE ingestion_id = %s
            """
        ).format(
            schema=sql.Identifier(self.SCHEMA),
            table=sql.Identifier(self.TABLE_NAME),
        )

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(delete_sql, (ingestion_id,))

    def _validate_table(self) -> None:
        """Fail fast if the vectors table or vector column is missing."""
        table_probe = sql.SQL(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = {schema}
              AND table_name = {table}
            """
        ).format(
            schema=sql.Literal(self.SCHEMA),
            table=sql.Literal(self.TABLE_NAME),
        )

        column_probe = sql.SQL(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = {schema}
              AND table_name = {table}
              AND column_name = 'vector'
            """
        ).format(
            schema=sql.Literal(self.SCHEMA),
            table=sql.Literal(self.TABLE_NAME),
        )

        try:
            with psycopg.connect(self._dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(table_probe)
                    if cur.rowcount == 0:
                        raise RuntimeError("vectors table missing")

                    cur.execute(column_probe)
                    if cur.rowcount == 0:
                        raise RuntimeError("vector column missing")

        except Exception as exc:
            raise RuntimeError(
                "PgVectorStore schema validation failed: "
                "table 'ingestion_service.vectors' missing or incompatible. "
                "Have you run Alembic migrations?"
            ) from exc
