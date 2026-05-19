from __future__ import annotations

import uuid

import pytest

from app.rag.vector_store import QdrantVectorStore


@pytest.mark.asyncio
async def test_memory_vector_store_filters_by_user_and_file() -> None:
    QdrantVectorStore._memory_points.clear()
    store = QdrantVectorStore()
    store._try_get_client = lambda: None
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    file_id = uuid.uuid4()
    other_file_id = uuid.uuid4()

    await store.upsert_chunks(
        [
            {
                "id": str(uuid.uuid4()),
                "vector": [1.0, 0.0],
                "payload": {"user_id": str(user_id), "file_id": str(file_id), "chunk_id": str(uuid.uuid4())},
            },
            {
                "id": str(uuid.uuid4()),
                "vector": [1.0, 0.0],
                "payload": {"user_id": str(user_id), "file_id": str(other_file_id), "chunk_id": str(uuid.uuid4())},
            },
            {
                "id": str(uuid.uuid4()),
                "vector": [1.0, 0.0],
                "payload": {"user_id": str(other_user_id), "file_id": str(file_id), "chunk_id": str(uuid.uuid4())},
            },
        ]
    )

    results = await store.search(query_vector=[1.0, 0.0], user_id=user_id, file_ids=[file_id], limit=10)

    assert len(results) == 1
    assert results[0]["payload"]["user_id"] == str(user_id)
    assert results[0]["payload"]["file_id"] == str(file_id)


@pytest.mark.asyncio
async def test_memory_vector_store_delete_by_file() -> None:
    QdrantVectorStore._memory_points.clear()
    store = QdrantVectorStore()
    store._try_get_client = lambda: None
    user_id = uuid.uuid4()
    file_id = uuid.uuid4()
    await store.upsert_chunks(
        [
            {
                "id": str(uuid.uuid4()),
                "vector": [1.0],
                "payload": {"user_id": str(user_id), "file_id": str(file_id), "chunk_id": str(uuid.uuid4())},
            }
        ]
    )

    await store.delete_by_file(user_id=user_id, file_id=file_id)
    results = await store.search(query_vector=[1.0], user_id=user_id, file_ids=[file_id], limit=10)

    assert results == []
