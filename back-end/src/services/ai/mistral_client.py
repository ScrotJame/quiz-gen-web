from __future__ import annotations

import logging
from typing import Any

import httpx
from mistralai.client import Mistral

from src.config import get_settings

logger = logging.getLogger(__name__)


def has_mistral_key() -> bool:
    """Kiểm tra xem API key của Mistral đã được cấu hình hợp lệ hay chưa."""
    settings = get_settings()
    key = (settings.mistral_api_key or "").strip().lower()
    return bool(key) and "your-key" not in key and not key.startswith("your-")


def get_mistral_client() -> Mistral | None:
    if not has_mistral_key():
        return None
    settings = get_settings()
    return Mistral(api_key=settings.mistral_api_key)


async def call_mistral_chat(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    model: str | None = None,
) -> str:
    """Gửi yêu cầu chat completion tới Mistral AI."""
    settings = get_settings()
    chosen_model = model or settings.mistral_model

    client = get_mistral_client()
    if not client:
        raise ValueError("MISTRAL_API_KEY chưa được cấu hình.")

    try:
        # Gọi trực tiếp qua async client của Mistral
        response = await client.chat.complete_async(
            model=chosen_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        choice = response.choices[0]
        content = choice.message.content
        if isinstance(content, str):
            return content
        return str(content)
    except Exception as e:
        logger.error(f"Lỗi khi gọi Mistral AI: {e}", exc_info=True)
        raise
