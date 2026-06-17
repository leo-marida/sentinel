"""
Embed code chunks with text-embedding-3-small and upsert to code_embeddings.
chunk_size=800, chunk_overlap=100 (spec Section 5 rule 5).
"""
import asyncio
import logging
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import AsyncOpenAI

from app.config import settings
from app.db.client import get_supabase

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

EMBED_BATCH_SIZE = 20  # OpenAI allows up to 2048 inputs per call; keep small for safety
EMBED_CONCURRENCY = 8  # max batches embedded at once, to stay within OpenAI rate limits
INSERT_BATCH_SIZE = 50  # rows per Supabase insert call; smaller payloads finish reliably within the 20s client timeout


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed a list of strings. Returns list of 1536-dim vectors."""
    if not texts:
        return []
    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


async def ingest_code_chunks(scan_id: str, files: list[dict]) -> None:
    """
    Chunk all scanned files, embed them, and upsert into code_embeddings.
    Called from the scanner node so the embeddings are ready for RAG in the analyzer.
    """
    if not files:
        return

    db = get_supabase()
    all_chunks: list[dict] = []

    for file in files:
        path = file["path"]
        content = file.get("content", "")
        if not content.strip():
            continue
        chunks = splitter.split_text(content)
        for idx, chunk in enumerate(chunks):
            all_chunks.append({
                "scan_id": scan_id,
                "file_path": path,
                "chunk_index": idx,
                "content": chunk,
                "metadata": {"path": path, "chunk_index": idx},
            })

    if not all_chunks:
        return

    logger.info("[embedder] Embedding %d chunks for scan %s", len(all_chunks), scan_id)

    batches = [
        all_chunks[i : i + EMBED_BATCH_SIZE]
        for i in range(0, len(all_chunks), EMBED_BATCH_SIZE)
    ]
    semaphore = asyncio.Semaphore(EMBED_CONCURRENCY)

    async def _embed_batch(batch: list[dict]) -> list[dict]:
        texts = [c["content"] for c in batch]
        async with semaphore:
            try:
                vectors = await embed_texts(texts)
            except Exception as e:
                logger.error("[embedder] Embedding batch failed: %s", e)
                return []
        return [
            {
                "scan_id": chunk["scan_id"],
                "file_path": chunk["file_path"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding": vector,
                "metadata": chunk["metadata"],
            }
            for chunk, vector in zip(batch, vectors)
        ]

    batch_results = await asyncio.gather(*[_embed_batch(b) for b in batches])
    rows = [row for batch_rows in batch_results for row in batch_rows]

    if not rows:
        return

    # Inserts run sequentially and directly (no asyncio.to_thread): this whole
    # pipeline already runs in its own isolated thread (see app/utils/background.py),
    # so blocking it briefly doesn't affect FastAPI's main loop. Handing the
    # Supabase client off to a *different* to_thread worker thread caused
    # cross-thread connection corruption ("EOF occurred in violation of
    # protocol") since each thread now owns its own client (app/db/client.py).
    # 50-row batches cut round trips ~2.5x over the original 20 while staying
    # small enough to finish within the client's 20s timeout (200-row batches
    # were big enough to occasionally stall the full request).
    insert_chunks = [
        rows[i : i + INSERT_BATCH_SIZE] for i in range(0, len(rows), INSERT_BATCH_SIZE)
    ]
    inserted = 0
    for chunk in insert_chunks:
        try:
            db.table("code_embeddings").insert(chunk).execute()
            inserted += len(chunk)
        except Exception as e:
            logger.error("[embedder] Insert batch failed: %s", e)

    logger.info("[embedder] Ingested %d/%d chunks for scan %s", inserted, len(rows), scan_id)