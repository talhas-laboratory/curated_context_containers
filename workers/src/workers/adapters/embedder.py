"""Embedding adapter for workers."""
from __future__ import annotations

import base64
import logging
from typing import List

import httpx

from workers.config import settings

LOGGER = logging.getLogger(__name__)
DEFAULT_GOOGLE_MODEL = "models/text-embedding-004"


class EmbeddingClient:
    def __init__(self) -> None:
        self.dim = settings.embedding_dims
        self.provider = getattr(settings, "embedder_provider", "nomic")
        self.api_key = settings.nomic_api_key
        self.api_url = settings.nomic_api_url
        self.image_model = getattr(settings, "nomic_image_model", "nomic-embed-image-v1")
        self.google_api_key = getattr(settings, "google_api_key", "") or ""
        self.google_model = getattr(settings, "google_embed_model", DEFAULT_GOOGLE_MODEL) or DEFAULT_GOOGLE_MODEL

    def _fallback(self, count: int) -> List[List[float]]:
        return [[0.0] * self.dim for _ in range(count)]

    def embed_text(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self.provider == "google":
            return self._embed_google(texts)
        if not self.api_key:
            return self._fallback(len(texts))
        payload = {
            "model": "nomic-embed-text-v1",
            "texts": texts,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = httpx.post(self.api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings") or data.get("data") or []
            if not embeddings:
                raise ValueError("No embeddings returned")
            cleaned: List[List[float]] = []
            for item in embeddings:
                if isinstance(item, list):
                    cleaned.append(item)
                elif isinstance(item, dict) and "embedding" in item:
                    cleaned.append(item["embedding"])
            if not cleaned:
                raise ValueError("Empty embeddings payload")
            return cleaned
        except Exception as exc:  # pragma: no cover - network disabled in tests
            LOGGER.warning("embedder_fallback", error=str(exc))
            return self._fallback(len(texts))

    def embed_image(self, images: List[bytes]) -> List[List[float]]:
        """Embed image bytes using provider or fall back to zeros."""
        if not images:
            return []
        if self.provider != "nomic":
            LOGGER.warning("embedder_image_provider_unsupported", provider=self.provider)
            return self._fallback(len(images))
        if not self.api_key:
            LOGGER.warning("embedder_image_no_key")
            return self._fallback(len(images))
        encoded = [base64.b64encode(img).decode("utf-8") for img in images]
        payload = {"model": self.image_model, "images": encoded}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = httpx.post(self.api_url, json=payload, headers=headers, timeout=15)
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
                raise ValueError("Empty image embeddings payload")
            return cleaned
        except Exception as exc:  # pragma: no cover - network disabled in tests
            LOGGER.warning("embedder_image_fallback", error=str(exc))
            return self._fallback(len(images))

    def _embed_google(self, texts: List[str]) -> List[List[float]]:
        if not self.google_api_key:
            LOGGER.warning("embedder_google_no_key")
            return self._fallback(len(texts))
        vectors: List[List[float]] = []
        for text in texts:
            payload = {"model": self.google_model, "content": {"parts": [{"text": text}]}}
            url = f"https://generativelanguage.googleapis.com/v1beta/{self.google_model}:embedContent"
            try:
                resp = httpx.post(url, params={"key": self.google_api_key}, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                embedding = ((data.get("embedding") or {}).get("values")) or []
                if not embedding:
                    raise ValueError("Empty embedding payload from Google")
                vectors.append(embedding)
            except Exception as exc:  # pragma: no cover - runtime guard
                LOGGER.warning("embedder_google_fallback", error=str(exc))
                vectors.append(self._fallback(1)[0])
        return vectors
