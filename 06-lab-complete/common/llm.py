"""Shared LLM factory for all agents.

Uses OpenRouter as an OpenAI-compatible API, so any provider's model
can be selected via the OPENROUTER_MODEL env var.
"""

import os

from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI client configured based on the available API key."""
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_API_KEY")
    if api_key:
        api_key = api_key.strip()
        
    # Check if this is an OpenRouter key
    if api_key and (api_key.startswith("sk-or-v1-") or os.getenv("OPENROUTER_API_KEY")):
        model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5")
        if not model or model == "openai/gpt-4o-mini":
            model = "openai/gpt-4o-mini"
        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.3,
            max_tokens=1024,
        )
    else:
        # Standard OpenAI API key or default fallback
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            temperature=0.3,
            max_tokens=1024,
        )