import json
import logging
from typing import AsyncGenerator, List, Optional
import httpx

from app.core.config import get_settings
from app.ai.interfaces import BaseEmbeddingProvider, BaseLLMProvider

logger = logging.getLogger("supportai.ai.providers.gemini")


class GeminiProvider(BaseEmbeddingProvider, BaseLLMProvider):
    """
    Implements Gemini embeddings and content generation using direct REST API calls.
    Uses 'text-embedding-004' for embeddings and 'gemini-1.5-flash' for completions.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Calls text-embedding-004 to generate 768-dimension vectors.
        """
        if not self.api_key or self.api_key == "AIzaSyDummyKeyForTesting":
            raise ValueError("Invalid Gemini API Key")

        url = f"{self.base_url}/models/text-embedding-004:batchEmbedContents?key={self.api_key}"
        payload = {
            "requests": [
                {
                    "model": "models/text-embedding-004",
                    "content": {"parts": [{"text": t}]}
                }
                for t in texts
            ]
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30.0)
            if resp.status_code != 200:
                logger.error(f"Gemini Embedding API error: {resp.text}")
                raise ValueError(f"Failed to generate embeddings: {resp.text}")
            
            data = resp.json()
            embeddings = data.get("embeddings", [])
            return [e["values"] for e in embeddings]

    async def generate_completion(
        self,
        system_prompt: str,
        prompt: str,
        history: Optional[List[dict]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> str:
        """
        Calls gemini-1.5-flash for completion.
        """
        if not self.api_key or self.api_key == "AIzaSyDummyKeyForTesting":
            raise ValueError("Invalid Gemini API Key")

        url = f"{self.base_url}/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        
        contents_payload = []
        if history:
            for msg in history:
                role = "model" if msg.get("role") in ("assistant", "model") else "user"
                contents_payload.append({
                    "role": role,
                    "parts": [{"text": msg.get("content")}]
                })
        
        contents_payload.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents_payload,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=60.0)
            if resp.status_code != 200:
                logger.error(f"Gemini Generation API error: {resp.text}")
                raise ValueError(f"Failed to generate content: {resp.text}")
            
            data = resp.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                logger.error(f"Malformed Gemini API response: {data}")
                raise ValueError("Malformed Gemini response payload") from e

    async def generate_completion_stream(
        self,
        system_prompt: str,
        prompt: str,
        history: Optional[List[dict]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """
        Streams completion tokens from gemini-1.5-flash.
        """
        if not self.api_key or self.api_key == "AIzaSyDummyKeyForTesting":
            raise ValueError("Invalid Gemini API Key")

        url = f"{self.base_url}/models/gemini-1.5-flash:streamGenerateContent?key={self.api_key}"

        contents_payload = []
        if history:
            for msg in history:
                role = "model" if msg.get("role") in ("assistant", "model") else "user"
                contents_payload.append({
                    "role": role,
                    "parts": [{"text": msg.get("content")}]
                })
        
        contents_payload.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents_payload,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, timeout=60.0) as response:
                if response.status_code != 200:
                    logger.error(f"Gemini Streaming API error: Status {response.status_code}")
                    raise ValueError("Failed to initialize streaming response")
                
                # Gemini streaming returns a JSON array or parts.
                # Let's iterate lines and extract texts.
                buffer = ""
                async for line in response.aiter_lines():
                    buffer += line.strip()
                    # A chunk might be enclosed in brackets or comma prefixed.
                    # We look for candidate JSON structures.
                    if buffer.startswith("["):
                        buffer = buffer[1:]
                    if buffer.endswith("]"):
                        buffer = buffer[:-1]
                    if buffer.startswith(","):
                        buffer = buffer[1:]
                    
                    if not buffer:
                        continue

                    try:
                        # Attempt to parse buffer
                        data = json.loads(buffer)
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        yield text
                        buffer = ""
                    except Exception:
                        # If incomplete JSON, continue reading stream
                        pass
