Here is the **Markdown-formatted README**—ready to drop directly into your repo, e.g. under:

`single_source_of_truth/architecture/embedding/EMBEDDING_GEMMA_README.md`

---

````markdown
# EmbeddingGemma Integration Guide  
_For LLC Agents — Implementing Gemma 3 Embeddings into Local Latent Containers_

## 0. Objective

Integrate **EmbeddingGemma** as a first-class embedding backend for LLC:

- Use it for **text embeddings** in ingestion and search.
- Keep the existing embedding adapter abstraction.
- Support two modes:
  - **Local open-weight model** (`google/embeddinggemma-300m`).
  - **Gemini API embedding** (`gemini-embedding-001`) as an optional cloud mode.

SearchService, Qdrant, and the Data Model remain unchanged.  
Only add a new embedder implementation + config support.

---

## 1. Context: Where Embeddings Are Used

Embedding calls occur in two main places:

### **Ingestion Pipeline**
- For each chunk:
  - `embedding = embedder.embed_documents([text])`
  - Write embedding to:
    - Qdrant vector collection
    - Optional: `embedding_cache` in Postgres

### **Search Pipeline**
- For each search request:
  - `query_vector = embedder.embed_query(query)`
  - Vector search → BM25 → RRF → dedup

Your task: implement a new embedder that plugs into both pipelines.

---

## 2. Configuration Schema

### 2.1. Manifest Additions

Extend the container manifest:

```yaml
embedding:
  kind: "embeddinggemma-local"            # or "embeddinggemma-gemini"
  model_name: "google/embeddinggemma-300m"
  dim: 768
  cache_ttl_s: 604800
````

Optional cloud mode:

```yaml
embedding:
  kind: "embeddinggemma-gemini"
  model_name: "gemini-embedding-001"
```

### 2.2. Environment Variables

| Mode       | Variable                            | Required |
| ---------- | ----------------------------------- | -------- |
| Local      | `EMBEDDINGGEMMA_DEVICE`             | No       |
| Gemini API | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Yes      |

Update `.env.example`.

---

## 3. Local EmbeddingGemma Implementation

### 3.1. Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
embeddinggemma = ["sentence-transformers>=3.0.0", "torch>=2.3.0"]
```

### 3.2. Embedder Class

Create:
`embedding/embeddinggemma.py`

```python
from typing import List
from sentence_transformers import SentenceTransformer

class EmbeddingGemmaLocal:
    def __init__(self, model_name="google/embeddinggemma-300m", device=None):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=device or "cpu")
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]
```

### 3.3. Integrate in EmbedderFactory

```python
def create_embedder(config: EmbedderConfig):
    if config.kind == "embeddinggemma-local":
        from embedding.embeddinggemma import EmbeddingGemmaLocal
        return EmbeddingGemmaLocal(config.model_name)
    if config.kind == "embeddinggemma-gemini":
        from embedding.embeddinggemma_gemini import EmbeddingGemmaGemini
        return EmbeddingGemmaGemini(config.model_name)
    # existing adapters...
```

---

## 4. Gemini API Embedding (Optional Cloud Mode)

### 4.1. Dependencies

```toml
[project.optional-dependencies]
gemini = ["google-genai>=0.2.0"]
```

### 4.2. Embedder Class

Create:
`embedding/embeddinggemma_gemini.py`

```python
import os
from google import genai
from google.genai import types as genai_types
from typing import List

class EmbeddingGemmaGemini:
    def __init__(self, model_name="gemini-embedding-001"):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        result = self.client.models.embed_content(
            model=self.model_name,
            contents=texts,
            config=genai_types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT"
            ),
        )
        return [e.values for e in result.embeddings]

    def embed_query(self, text: str) -> List[float]:
        result = self.client.models.embed_content(
            model=self.model_name,
            contents=[text],
            config=genai_types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY"
            ),
        )
        return result.embeddings[0].values
```

---

## 5. Ingestion & Search Integration

### 5.1. Ingestion Worker

Pseudo-logic:

```python
embedder = create_embedder(container_manifest.embedding)

for chunk in chunks:
    cache_key = (hash(chunk.text), embedder.model_name)
    cached = embedding_cache.get(cache_key)
    if cached:
        embedding = cached
    else:
        embedding = embedder.embed_documents([chunk.text])[0]
        embedding_cache.put(cache_key, embedding)

    qdrant_upsert(container_id, chunk.id, embedding, payload=...)
```

### 5.2. SearchService

```python
embedder = create_embedder(container_manifest.embedding)
query_vec = embedder.embed_query(query)
# run vector search → bm25 → rrf → dedup
```

If embedding fails, emit issue code:
`EMBEDDING_DOWN`
and fall back to pure BM25.

---

## 6. Testing Plan

### 6.1. Unit Tests

* Test embedding shape and dimension.
* Validate deterministic output for repeated calls.
* Test API-key-required path for Gemini embedder.

### 6.2. Ingest→Search Integration Test

Use your existing **three art sources** and **golden queries**.

Expected results:

* No more `NO_HITS`.
* nDCG/recall > 0 for most queries.
* Latency within manifest budgets.

---

## 7. Fallback & Error Handling

* If model cannot load → raise clear startup error.
* Do **not** silently fallback to zero vectors.
* If API key missing → `EMBEDDING_DOWN` issue.

---

## 8. Documentation Updates

Update:

* `SYSTEM.md` — list EmbeddingGemma under embedding adapters.
* `DATA_MODEL.md` — document `embedding_cache.model_key`.
* `runbooks/SETUP_AND_INSTALL.md` — new dependencies + API key instructions.
* `DECISIONS.md` — EmbeddingGemma is Phase-1 default for text containers.

---

## 9. Summary

EmbeddingGemma provides:

* Strong text retrieval performance
* Open weights
* Full local execution
* Optional Gemini API integration

This guide gives the entire implementation path for adding it as a new embedding adapter in the Local Latent Containers architecture.

Agents should follow this file step-by-step when implementing or modifying EmbeddingGemma support.

```

