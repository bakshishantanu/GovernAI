"""Reading text off an image, for documents that have none to extract.

A scanned PDF is a stack of photographs. `pypdf` finds nothing in it, so
without this a 15-page scanned assignment uploads, fails, and tells the user
their file needs OCR. This is that OCR.

Why a vision model rather than Tesseract: no system binary to install (which
matters on Windows, where Tesseract is a separate installer, not a pip
package), and far better results on exactly the inputs people actually
upload. Verified against two real samples before this was written: a
photographed handwritten notebook, complete with spiral binding, page skew and
desk clutter, and a degraded 1971 typewritten letter. Both transcribed
essentially correctly, including a handwritten registration number.
"""

from __future__ import annotations

import asyncio
import base64
from abc import ABC, abstractmethod

import httpx

from app.runtime.rag.embeddings import retry_delay_seconds

#: Deliberately not "describe this image". The output goes straight into a
#: chunk that will be embedded and quoted back with a citation, so any
#: commentary from the model becomes text the document does not contain.
OCR_PROMPT = (
    "Transcribe all text in this image exactly as written, preserving line "
    "breaks and reading order. Output only the transcription, with no "
    "commentary, no markdown fences, and no description of the image. If the "
    "image contains no legible text, output nothing at all."
)


class OcrProvider(ABC):
    """Turns an image into the text printed or written on it."""

    @abstractmethod
    async def read(self, image_bytes: bytes, mime_type: str) -> str: ...


class GeminiVisionOcr(OcrProvider):
    """OCR via Gemini's multimodal generateContent.

    The model is configurable because Google retires them: `gemini-2.5-flash`,
    which this project still names as its LLM fallback, already answers 404
    with "no longer available to new users" on this API key. A hardcoded model
    name here would be a time bomb of exactly that shape.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    MAX_RETRIES = 4
    BASE_BACKOFF_SECONDS = 10

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        # Generous: a dense page of handwriting is genuinely slow to read.
        self._client = client or httpx.AsyncClient(timeout=120.0)

    async def read(self, image_bytes: bytes, mime_type: str) -> str:
        url = f"{self.BASE_URL}/{self._model}:generateContent"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": OCR_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(image_bytes).decode(),
                            }
                        },
                    ]
                }
            ]
        }

        last_error: httpx.HTTPStatusError | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            response = await self._client.post(
                url, headers={"x-goog-api-key": self._api_key}, json=payload
            )
            if response.status_code not in (429, 503):
                response.raise_for_status()
                return _text_from_response(response.json())

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_error = exc
            if attempt == self.MAX_RETRIES:
                break
            await asyncio.sleep(
                retry_delay_seconds(response, attempt, self.BASE_BACKOFF_SECONDS)
            )

        assert last_error is not None
        raise last_error


def _text_from_response(body: dict) -> str:
    """The transcription, or empty string if the model returned nothing.

    A blank page legitimately produces no candidates and no parts, and that is
    not an error: the caller skips pages with no text either way.
    """
    candidates = body.get("candidates") or []
    if not candidates:
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(part.get("text", "") for part in parts).strip()


def build_ocr_provider_from_settings() -> OcrProvider | None:
    """The configured OCR backend, or None when no key is available.

    None is a real state, not a failure: without it, uploads of scanned files
    are refused up front with a message saying so, which is better than
    accepting one and silently indexing nothing.
    """
    from app.config import settings

    if not settings.GEMINI_API_KEY:
        return None
    return GeminiVisionOcr(
        api_key=settings.GEMINI_API_KEY, model=settings.OCR_MODEL
    )
