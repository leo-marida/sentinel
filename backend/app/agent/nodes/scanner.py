"""
Scanner node: fetches repo files, runs Semgrep + Bandit, and embeds code chunks.
"""
import logging

from app.agent.state import SentinelState
from app.rag.embedder import ingest_code_chunks
from app.services.github_service import fetch_repo_files
from app.services.scanner_service import scan_files

logger = logging.getLogger(__name__)


async def run(state: SentinelState) -> dict:
    logger.info("[scanner] Fetching files for %s", state["repo_url"])
    files = await fetch_repo_files(state["repo_url"], max_files=100)

    logger.info("[scanner] Running scanners on %d files", len(files))
    raw_findings = await scan_files(files)
    logger.info("[scanner] Found %d raw findings", len(raw_findings))

    # Embed code chunks for RAG (non-blocking — failures logged, not raised)
    try:
        await ingest_code_chunks(state["scan_id"], files)
    except Exception as e:
        logger.warning("[scanner] Code embedding failed (non-fatal): %s", e)

    return {
        "files": files,
        "raw_findings": raw_findings,
        "current_node": "scanner",
    }