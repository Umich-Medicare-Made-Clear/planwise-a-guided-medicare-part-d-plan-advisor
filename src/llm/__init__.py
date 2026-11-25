"""LLM backends. Agents only talk to the `LLM` interface, never a vendor SDK.

Mode is picked by get_llm(mode) or the PLANWISE_MODE env var (default "dev"):
    dev   local Ollama model (free, offline)
    prod  Gemini 2.5 Flash-Lite, needs GEMINI_API_KEY

Other env vars: PLANWISE_MODEL (override the model for the chosen mode),
PLANWISE_NUM_CTX and OLLAMA_HOST (dev only).
"""
from __future__ import annotations

import os

from src.llm.base import LLM, LLMError, LLMReply, parse_json

DEV_MODEL = "qwen2.5:7b-instruct"
PROD_MODEL = "gemini-2.5-flash-lite"
DEFAULT_NUM_CTX = 16384
MODES = ("dev", "prod")


def get_llm(mode: str | None = None) -> LLM:
    mode = (mode or os.getenv("PLANWISE_MODE", "dev")).lower()
    if mode not in MODES:
        raise ValueError(f"Unknown mode {mode!r}; expected one of {MODES}")

    # imported here so dev doesn't need google-genai installed, and vice versa
    if mode == "prod":
        from src.llm.gemini_backend import GeminiLLM
        return GeminiLLM(model=os.getenv("PLANWISE_MODEL", PROD_MODEL))

    from src.llm.ollama_backend import OllamaLLM
    return OllamaLLM(
        model=os.getenv("PLANWISE_MODEL", DEV_MODEL),
        num_ctx=int(os.getenv("PLANWISE_NUM_CTX", DEFAULT_NUM_CTX)),
        host=os.getenv("OLLAMA_HOST"),
    )


__all__ = ["LLM", "LLMError", "LLMReply", "MODES", "get_llm", "parse_json"]
