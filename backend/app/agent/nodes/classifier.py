"""
Uses gpt-4.1-mini for fast, cheap triage classification.
Processes findings in batches of 20 to avoid token-limit truncation.
"""
import json
import logging
import uuid

from openai import AsyncOpenAI

from app.agent.state import Finding, SentinelState
from app.config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

CLASSIFY_SYSTEM = """You are a security triage expert. Given a list of raw scanner findings,
classify each one. Return ONLY valid JSON with a top-level key "findings" containing an array.
Each element must have: id (copy from input), severity (critical|high|medium|low|info),
title (short, max 120 chars), description (1-2 sentences). Be concise. Do not invent findings."""

BATCH_SIZE = 20


async def _classify_batch(batch: list[dict]) -> list[dict]:
    """Classify a single batch of raw findings. Returns classified list."""
    raw_text = json.dumps(batch, indent=2)
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_FAST_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": CLASSIFY_SYSTEM},
                {"role": "user", "content": f"Classify these findings:\n{raw_text}"},
            ],
            max_tokens=4096,
        )
        data = json.loads(response.choices[0].message.content)
        return data.get("findings", [])
    except Exception as e:
        logger.error("Classifier batch failed: %s", e)
        return []


async def run(state: SentinelState) -> dict:
    if not state.get("raw_findings"):
        return {"findings": [], "current_node": "classifier"}

    raw = state["raw_findings"][:100]  # hard cap at 100 total
    classified_map: dict[int, dict] = {}

    for start in range(0, len(raw), BATCH_SIZE):
        batch = raw[start : start + BATCH_SIZE]
        classified = await _classify_batch(batch)
        for j, item in enumerate(classified):
            classified_map[start + j] = item

    findings: list[Finding] = []
    for i, raw_item in enumerate(raw):
        enriched = classified_map.get(i, {})
        findings.append(Finding(
            id=str(uuid.uuid4()),
            file_path=raw_item.get("path", raw_item.get("filename", "unknown")),
            line_start=raw_item.get("start", {}).get("line", 0),
            line_end=raw_item.get("end", {}).get("line", 0),
            rule_id=raw_item.get("check_id", raw_item.get("test_id", "unknown")),
            severity=enriched.get("severity", "medium"),
            title=enriched.get("title", raw_item.get("extra", {}).get("message", "Finding")[:120]),
            description=enriched.get("description", ""),
            raw_output=raw_item,
            ai_analysis=None,
            remediation=None,
            approval_status="pending",
        ))

    logger.info("Classifier produced %d findings", len(findings))
    return {"findings": findings, "current_node": "classifier"}