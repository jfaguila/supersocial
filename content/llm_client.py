"""
LLM client abstraction.
Supports OpenAI (primary) with Anthropic as fallback.
Structured output via JSON mode enforced.
"""
import json
import time
from dataclasses import dataclass
from typing import Optional

import openai

from config.settings import get_settings


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    duration_ms: int
    is_fallback: bool = False


class LLMClient:
    def __init__(self):
        self._settings = get_settings()
        self._openai = openai.AsyncOpenAI(api_key=self._settings.openai_api_key)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "text",  # "text" | "json_object"
        max_tokens: int = 1024,
        temperature: float = 0.8,
    ) -> LLMResponse:
        start = int(time.time() * 1000)
        is_fallback = False
        content = ""
        model = self._settings.openai_model
        prompt_tokens = 0
        completion_tokens = 0

        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if response_format == "json_object":
                kwargs["response_format"] = {"type": "json_object"}

            response = await self._openai.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens

        except (openai.APIError, openai.RateLimitError) as e:
            # Fallback to Anthropic if configured
            if self._settings.anthropic_api_key:
                content, prompt_tokens, completion_tokens = await self._anthropic_fallback(
                    system_prompt, user_prompt, max_tokens
                )
                model = "claude-3-haiku-20240307"
                is_fallback = True
            else:
                raise

        return LLMResponse(
            content=content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=int(time.time() * 1000) - start,
            is_fallback=is_fallback,
        )

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        response = await self.generate(system_prompt, user_prompt, response_format="json_object")
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"raw": response.content}

    async def _anthropic_fallback(
        self, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> tuple[str, int, int]:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = message.content[0].text if message.content else ""
        return content, message.usage.input_tokens, message.usage.output_tokens
