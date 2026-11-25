from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPT_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    # Keep system prompts byte-identical between calls (no dates/IDs/user data)
    # so prefix caching works. Per-request data goes in the user message.
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        available = sorted(p.stem for p in PROMPT_DIR.glob("*.md"))
        raise FileNotFoundError(f"No prompt named {name!r}. Available: {available}")
    return path.read_text(encoding="utf-8").strip()
