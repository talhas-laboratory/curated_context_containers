"""Embedding adapter for MCP server."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from typing import List

import httpx
import numpy as np

from app.core.config import get_settings

LOGGER = logging.getLogger(__name__)

DEFAULT_CACHE_SIZE = 64
DEFAULT_GOOGLE_MODEL = "models/text-embedding-004"
DEFAULT_IMAGE_MODEL = "nomic-embed-image-v1"


class EmbeddingError(RuntimeError):
    """Raised when embedding provider cannot serve a request."""


class EmbeddingClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.default_dim = settings.embedding_dims
        self.provider = getattr(settings, "embedder_provider", "nomic")
        self.nomic_api_key = settings.nomic_api_key
        self.nomic_api_url = getattr(settings, "nomic_api_url", "https://api-atlas.nomic.ai/v1/embedding/text")
        self.nomic_image_url = getattr(settings, "nomic_image_url", "https://api-atlas.nomic.ai/v1/embedding/image")
        self.nomic_image_model = getattr(settings, "nomic_image_model", DEFAULT_IMAGE_MODEL) or DEFAULT_IMAGE_MODEL
        self.google_api_key = getattr(settings, "google_api_key", "") or ""
        self.google_embed_model = getattr(settings, "google_embed_model", DEFAULT_GOOGLE_MODEL) or DEFAULT_GOOGLE_MODEL
        self.batch_size = getattr(settings, "embedding_batch_size", 32)
        self.rate_limit_delay = getattr(settings, "embedding_rate_limit_delay", 0.1)
        self.cache: dict[str, List[float]] = {}
        self.cache_size = getattr(settings, "embedding_cache_size", DEFAULT_CACHE_SIZE)

    def _fallback(self, size: int) -> List[List[float]]:
        """Return zero vectors as fallback."""
        return [[0.0] * self.default_dim for _ in range(size)]

    def _normalize_vectors(self, vectors: List[List[float]]) -> List[List[float]]:
        """L2 normalize vectors for cosine similarity."""
        
        if not vectors:
            return []
        
        arr = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)  # Avoid division by zero
        normalized = arr / norms
        return normalized.tolist()

    def _cache_key(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _remember(self, key: str, vector: List[float]) -> None:
        if self.cache_size <= 0:
            return
        if len(self.cache) >= self.cache_size:
            # Drop an arbitrary key to keep bookkeeping simple.
            drop_key = next(iter(self.cache.keys()))
            self.cache.pop(drop_key, None)
        self.cache[key] = vector

    async def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Embed texts asynchronously with batching, caching, and rate limiting."""
        if not texts:
            return []
        if self.provider == "google":
            if not self.google_api_key:
                LOGGER.warning("No Google API key, using fallback embeddings")
                return self._fallback(len(texts))
            return await self._embed_google(texts)

        if not self.nomic_api_key:
            LOGGER.warning("No Nomic API key, using fallback embeddings")
            return self._fallback(len(texts))

        vectors_by_key: dict[str, List[float]] = {}
        missing: list[tuple[str, str]] = []

        for text in texts:
            key = self._cache_key(text)
            cached = self.cache.get(key)
            if cached is not None:
                vectors_by_key[key] = cached
                continue
            missing.append((key, text))

        async with httpx.AsyncClient(timeout=30.0) as client:
            for idx in range(0, len(missing), self.batch_size):
                batch = missing[idx : idx + self.batch_size]
                _, batch_texts = zip(*batch) if batch else ([], [])
                if not batch_texts:
                    continue
                embeddings = await self._embed_batch_async(client, list(batch_texts))
                for (key, _text), vector in zip(batch, embeddings):
                    self._remember(key, vector)
                    vectors_by_key[key] = vector
                if idx + self.batch_size < len(missing):
                    await asyncio.sleep(self.rate_limit_delay)

        # Preserve ordering relative to inputs
        ordered: List[List[float]] = []
        for text in texts:
            key = self._cache_key(text)
            vector = vectors_by_key.get(key)
            if vector is None:
                # Should not happen, but avoid crashing pipeline.
                vector = self._fallback(1)[0]
            ordered.append(vector)
        return ordered

    async def embed_image(self, images: List[bytes]) -> List[List[float]]:
        """Embed image bytes using provider or fall back to zeros."""
        if not images:
            return []
        if self.provider != "nomic":
            LOGGER.warning("embed_image_provider_unsupported", extra={"provider": self.provider})
            return self._fallback(len(images))
        if not self.nomic_api_key:
            LOGGER.warning("embed_image_missing_key")
            return self._fallback(len(images))

        payload = {"model": self.nomic_image_model, "images": [base64.b64encode(img).decode("utf-8") for img in images]}
        headers = {
            "Authorization": f"Bearer {self.nomic_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(self.nomic_image_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings") or data.get("data") or []
                cleaned: List[List[float]] = []
                for item in embeddings:
                    if isinstance(item, list):
                        cleaned.append(item)
                    elif isinstance(item, dict) and "embedding" in item:
                        cleaned.append(item["embedding"])
                if not cleaned:
                    raise EmbeddingError("Empty image embeddings payload")
                return self._normalize_vectors(cleaned)
            except Exception as exc:
                LOGGER.error("embed_image_failed", extra={"error": str(exc)})
                raise EmbeddingError(str(exc)) from exc

    async def _embed_google(self, texts: List[str]) -> List[List[float]]:
        """Embed using Google embedding endpoint (Gemma/Gemini)."""
        # Simple per-text calls to keep contract deterministic; small batch sizes.
        vectors: List[List[float]] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for text in texts:
                payload = {
                    "model": self.google_embed_model,
                    "content": {"parts": [{"text": text}]},
                }
                url = f"https://generativelanguage.googleapis.com/v1beta/{self.google_embed_model}:embedContent"
                try:
                    resp = await client.post(url, params={"key": self.google_api_key}, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    embedding = ((data.get("embedding") or {}).get("values")) or []
                    if not embedding:
                        raise EmbeddingError("Empty embedding payload from Google")
                    vectors.append(self._normalize_vectors([embedding])[0])
                except Exception as exc:
                    LOGGER.error("google_embedding_failed", extra={"error": str(exc)})
                    raise EmbeddingError(str(exc)) from exc
        return vectors

    async def _embed_batch_async(self, client: httpx.AsyncClient, texts: List[str]) -> List[List[float]]:
        """Embed a single batch of texts asynchronously."""
        payload = {"model": "nomic-embed-text-v1", "texts": texts}
        headers = {
            "Authorization": f"Bearer {self.nomic_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await client.post(self.nomic_api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings") or data.get("data") or []
            cleaned: List[List[float]] = []
            for item in embeddings:
                if isinstance(item, list):
                    cleaned.append(item)
                elif isinstance(item, dict) and "embedding" in item:
                    cleaned.append(item["embedding"])

            if not cleaned:
                raise EmbeddingError("Empty embedding payload from API")

            if len(cleaned) != len(texts):
                LOGGER.warning(
                    "embedding_count_mismatch",
                    extra={"expected": len(texts), "received": len(cleaned)},
                )

            return self._normalize_vectors(cleaned)
        except Exception as exc:
            LOGGER.error("embedding_batch_failed", exc_info=exc)
            raise EmbeddingError(str(exc)) from exc


embedding_client = EmbeddingClient()
