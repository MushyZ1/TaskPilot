from abc import ABC, abstractmethod
from ollama import chat
import os
from openai import OpenAI


class LLMProvider(ABC):

    @abstractmethod
    def generate(self, messages: list, response_format: dict) -> str:
        pass


class OllamaProvider(LLMProvider):

    def generate(self, messages: list, response_format: dict) -> str:

        response = chat(
            model="qwen3:4b",
            messages=messages,
            format=response_format,
            think=False
        )

        content = response.message.content

        if content is None:
            raise ValueError("LLM returned an empty response")

        return content


class OpenAICompatibleProvider(LLMProvider):

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )

        self.model = os.getenv("LLM_MODEL")


    def generate(self, messages: list, response_format: dict) -> str:

        if not self.model:
            raise ValueError("LLM_MODEL environment variable is not set")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_decision",
                    "schema": response_format,
                    "strict": True
                }
            }
        )

        content = response.choices[0].message.content

        if content is None:
            raise ValueError("LLM returned an empty response")

        return content


def get_provider():

    provider_name = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider_name == "ollama":
        return OllamaProvider()

    elif provider_name == "openai":
        return OpenAICompatibleProvider()

    else:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")
