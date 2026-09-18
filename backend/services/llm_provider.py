from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(Exception):
    pass


class BaseLLMProvider(ABC):
    @abstractmethod
    async def structured_completion(
        self, system_prompt: str, user_message: str, output_schema: type[T]
    ) -> T:
        ...


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        logger.info("GeminiProvider pronto: model=%s", model)

    async def structured_completion(
        self, system_prompt: str, user_message: str, output_schema: type[T]
    ) -> T:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=f"{system_prompt}\n\n{user_message}",
                config={
                    "response_mime_type": "application/json",
                    "response_schema": output_schema,
                    "temperature": 0.1,
                },
            )

            result = response.parsed
            if result is None:
                raise LLMProviderError(
                    f"Risposta vuota da Gemini per lo schema {output_schema.__name__}."
                )

            return result

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"Errore chiamata Gemini ({output_schema.__name__}): {e}") from e


def create_llm_provider() -> BaseLLMProvider:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent.parent / ".env"
    load_dotenv(env_file, override=True)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key or api_key in ("la-tua-api-key-qui", "YOUR_API_KEY"):
        from services.mock_provider import MockLLMProvider

        logger.warning("GEMINI_API_KEY assente: uso MockLLMProvider.")
        return MockLLMProvider()

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    return GeminiProvider(api_key=api_key, model=model)
