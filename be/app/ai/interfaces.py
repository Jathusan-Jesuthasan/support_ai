from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional


class BaseEmbeddingProvider(ABC):
    """
    Abstractions for embedding generation providers.
    """

    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates 768-dimension vectors for input text fragments.
        """
        pass


class BaseLLMProvider(ABC):
    """
    Abstractions for generative chat LLM providers.
    """

    @abstractmethod
    async def generate_completion(
        self,
        system_prompt: str,
        prompt: str,
        history: Optional[List[dict]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> str:
        """
        Generates a text completion response.
        """
        pass

    @abstractmethod
    async def generate_completion_stream(
        self,
        system_prompt: str,
        prompt: str,
        history: Optional[List[dict]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """
        Streams text completion tokens.
        """
        yield ""
