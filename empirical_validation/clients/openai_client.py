from __future__ import annotations

from openai import OpenAI
from clients.base import LLMClient


class OpenAILLMClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=0.2,
        )
        return response.output_text
