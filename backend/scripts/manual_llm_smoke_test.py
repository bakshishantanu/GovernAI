"""Manually verify Groq/Gemini keys actually work end-to-end.

Not part of the pytest suite on purpose - this makes real network calls and
needs real API keys, neither of which belong in CI. Run it yourself locally:

    .venv/Scripts/python.exe scripts/manual_llm_smoke_test.py
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.runtime.llm.gemini import GeminiProvider
from app.runtime.llm.groq import GroqProvider

PROMPT = [{"role": "user", "content": "Reply with exactly the word: pong"}]


async def _check(name: str, provider) -> None:
    try:
        response = await provider.chat(PROMPT)
    except Exception as exc:
        print(f"[{name}] FAILED: {exc}")
        return
    print(f"[{name}] OK - model={response.model} content={response.content!r} usage={response.usage}")


async def main() -> None:
    load_dotenv()

    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if not groq_key and not gemini_key:
        print("No API keys found. Copy backend/.env.example to backend/.env and fill in real keys.")
        return

    if groq_key:
        await _check("groq", GroqProvider(api_key=groq_key))
    else:
        print("[groq] skipped - GROQ_API_KEY not set")

    if gemini_key:
        await _check("gemini", GeminiProvider(api_key=gemini_key))
    else:
        print("[gemini] skipped - GEMINI_API_KEY not set")


if __name__ == "__main__":
    asyncio.run(main())
