# ingestion_service/src/core/models_v2/document_node.py
"""
ORM model for DocumentNodes table using pgvector.
"""

from typing import TYPE_CHECKING
from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from core.models import Base
import uuid

from pgvector.sqlalchemy import Vector  # pgvector type

if TYPE_CHECKING:
    from .vector_chunk import VectorChunk


class DocumentNode(Base):
    """
    Represents a logical document, the unit of retrieval for structured RAG.

    Attributes:
        document_id: Primary key UUID.
        title: Document title.
        summary: Text summary of the document.
        summary_embedding: 768-dimensional embedding vector (pgvector).
        source: Source name or URI.
        ingestion_id: Foreign key to the ingestion request.
        doc_type: Type/category of the document.
        vector_chunks: List of related VectorChunks.
    """
    __tablename__ = "document_nodes"
    __table_args__ = {"schema": "ingestion_service"}

    document_id: str = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title: str = Column(String, nullable=False)
    summary: str = Column(Text, nullable=False)
    summary_embedding: list[float] = Column(Vector(768), nullable=True)  # pgvector
    source: str = Column(String, nullable=False)
    ingestion_id: str = Column(String, ForeignKey("ingestion_service.ingestion_requests.ingestion_id"), nullable=False)
    doc_type: str = Column(String, nullable=False)

    # Relationship to VectorChunks
    vector_chunks: "list[VectorChunk]" = relationship("VectorChunk", back_populates="document_node")
