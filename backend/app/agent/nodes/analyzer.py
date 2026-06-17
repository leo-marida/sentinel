"""
Analyzer node: deep analysis with gpt-4o on critical/high findings.
Uses pgvector RAG to pull similar historical vulnerabilities as context.
"""
import logging

from openai import AsyncOpenAI

from app.agent.state import SentinelState
from app.config import settings
from app.rag.retriever import retrieve_similar_vulns

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

ANALYZE_SYSTEM = """You are a senior application security engineer.
Analyze the security finding and provide:
1. Root cause explanation (2-3 sentences)
2. Concrete remediation steps (numbered list, code examples where helpful)
3. Severity justification
Be precise and actionable. Reference the similar historical vulnerabilities provided."""


async def run(state: SentinelState) -> dict:
    critical_high = [
        f for f in state.get("findings", [])
        if f["severity"] in ("critical", "high")
    ]

    if not critical_high:
        logger.info("[analyzer] No critical/high findings — skipping deep analysis")
        return {"current_node": "analyzer"}

    updated_findings = list(state["findings"])

    for finding in critical_high:
        logger.info("[analyzer] Analyzing: %s", finding["title"])

        # RAG: fetch similar historical vulnerabilities
        similar = await retrieve_similar_vulns(
            query=f"{finding['title']} {finding['description']}",
            top_k=3,
        )
        context_text = "\n\n".join([
            f"[Similar: {v['title']}]\n{v['remediation']}"
            for v in similar
        ]) or "No similar historical findings available."

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_SMART_MODEL,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": ANALYZE_SYSTEM},
                    {"role": "user", "content": (
                        f"**Finding:** {finding['title']}\n"
                        f"**File:** {finding['file_path']} (line {finding['line_start']})\n"
                        f"**Description:** {finding['description']}\n\n"
                        f"**Similar historical vulnerabilities:**\n{context_text}"
                    )},
                ],
                max_tokens=800,
            )
            analysis = response.choices[0].message.content
        except Exception as e:
            logger.error("[analyzer] LLM call failed for %s: %s", finding["id"], e)
            analysis = "Analysis unavailable."

        for i, f in enumerate(updated_findings):
            if f["id"] == finding["id"]:
                updated_findings[i] = {**f, "ai_analysis": analysis}
                break

    return {"findings": updated_findings, "current_node": "analyzer"}