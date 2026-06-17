"""
pgvector cosine similarity search against the vuln_knowledge table.
Uses Supabase RPC to call a SQL function that runs the vector query.
"""
import logging

from openai import AsyncOpenAI

from app.config import settings
from app.db.client import get_supabase

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def _embed_query(text: str) -> list[float]:
    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=[text],
    )
    return response.data[0].embedding


async def retrieve_similar_vulns(query: str, top_k: int = 3) -> list[dict]:
    """
    Embed the query and retrieve the top-k most similar entries
    from vuln_knowledge via pgvector cosine similarity.
    Returns list of {title, description, remediation, severity, similarity}.
    """
    try:
        embedding = await _embed_query(query)
        db = get_supabase()
        result = db.rpc(
            "match_vuln_knowledge",
            {"query_embedding": embedding, "match_count": top_k},
        ).execute()
        return result.data or []
    except Exception as e:
        logger.warning("[retriever] RAG query failed: %s", e)
        return []