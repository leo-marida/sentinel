"""
Supabase-backed LangGraph checkpoint saver.
Stores graph state in the agent_checkpoints table so HITL survives server restarts.
"""
import json
import logging
from typing import Any, AsyncIterator, Iterator, Optional, Sequence, Tuple

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

from app.db.client import get_supabase

logger = logging.getLogger(__name__)


class SupabaseCheckpointer(BaseCheckpointSaver):
    """Minimal Supabase checkpoint saver for LangGraph HITL."""

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        db = get_supabase()
        try:
            result = (
                db.table("agent_checkpoints")
                .select("*")
                .eq("thread_id", thread_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if not result.data:
                return None
            row = result.data[0]
            checkpoint = self.serde.loads_typed(
                (row["checkpoint"]["type"], row["checkpoint"]["data"])
            )
            metadata = row.get("metadata") or {}
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=CheckpointMetadata(**metadata),
                parent_config=None,
            )
        except Exception as e:
            logger.error("Checkpoint get failed: %s", e)
            return None

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        return iter([])

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Any,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        db = get_supabase()
        try:
            type_, data = self.serde.dumps_typed(checkpoint)
            db.table("agent_checkpoints").upsert({
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "checkpoint": {"type": type_, "data": data},
                "metadata": dict(metadata),
            }).execute()
        except Exception as e:
            logger.error("Checkpoint put failed: %s", e)
        return {**config, "configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        return self.get_tuple(config)

    async def alist(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        return
        yield  # make it an async generator

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Any,
    ) -> RunnableConfig:
        return self.put(config, checkpoint, metadata, new_versions)