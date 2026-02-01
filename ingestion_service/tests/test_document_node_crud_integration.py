# tests/test_document_node_crud_integration.py
import pytest
from ingestion_service.src.core.crud import create_document_node, get_document_node

@pytest.mark.docker
@pytest.mark.integration
def test_document_node_crud(session):
    node = create_document_node(
        session,
        document_id="crud-id",
        ingestion_id="ingest-1",
        title="CRUD Test",
        text="Lorem Ipsum",
        metadata={}
    )

    fetched = get_document_node(session, "crud-id")
    assert fetched is not None
    assert fetched.title == "CRUD Test"
