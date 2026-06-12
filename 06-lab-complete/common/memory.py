"""Shared conversation memory singleton (Challenge 1).

Wraps LangGraph's MemorySaver so all agents share one in-process checkpointer.
Conversation history is keyed by thread_id=context_id, giving per-conversation
isolation. History survives across multiple tool calls within a session but
resets on server restart (swap for SqliteSaver/PostgresSaver for persistence).
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

_checkpointer: MemorySaver | None = None


def get_checkpointer() -> MemorySaver:
    """Return the process-wide MemorySaver (lazy-init singleton)."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer
