Here’s the distilled essence of your project — the why, what, and how — written as if for your internal README or investor deck:
Project: Local Latent Containers
Vision
To create a modular cognition layer for AI — a system where different “context containers” hold thematic knowledge (art, science, philosophy, etc.) and can be accessed by any intelligent agent, locally or via MCP. It’s the foundation of a world where intelligence becomes composable — agents mix, match, and reason over curated fragments of reality, all stored in vector space.
“A personal memory architecture for AI — calm, local, and precise.”
Core Idea
Each container is a self-contained vector database (and metadata layer) that represents a specific domain of context — for example:
* expressionist_art
* quantum_mechanics
* ancient_texts
* personal_journal
Each container can ingest data from any modality: text, PDFs, web pages, images, audio, or short videos — embedding all into a shared semantic space using Nomic Embed Multimodal 7B.
These containers can then be queried, fused, or compared by agents — locally or remotely — through an MCP server interface, turning your device into a modular knowledge ecosystem.
Purpose
1. For humans: give creators, researchers, and thinkers a way to store, structure, and retrieve their universe of meaning — locally, privately, intelligently.
2. For agents: act as a composable knowledge substrate; an “intelligence plugboard” for context-aware AI reasoning.
Product Philosophy
* Calm technology — interfaces breathe, not shout.
* Deterministic systems — logic never guesses.
* Composability over centralization — intelligence comes from combining small, well-defined parts.
* Local-first design — no cloud dependency, full data sovereignty.
* Cross-modal cognition — text, images, and media share one latent geometry.
Architecture Overview
* Frontend: Designed by the IKB Human Cognition Architect persona — minimalist, perceptually calm UI with deep information design rooted in the IKB Zen Cognition System.
* Backend: Engineered by the Silent Architect persona — deterministic FastAPI-based MCP server managing vector stores, provenance logs, and retrieval pipelines.
* Core Logic: Hybrid retrieval (dense + BM25 + optional rerank) with diagnostics, provenance, and customizable container-level policies.
* Storage: Qdrant (vectors), Postgres (metadata), MinIO (blobs).
* Access: Local MCP interface allowing connection to external models (ChatGPT, Claude, or local agents).
What It Enables
* Agents can “borrow” themed intelligence — e.g., query the Expressionist Art container for visual metaphor references while reasoning about design.
* You can DM a Telegram bot or upload files to instantly embed them into chosen containers.
* Each container becomes a semantic library you can search, remix, and extend — like modular pieces of your own digital memory.
Long-Term Vision
To evolve into a “cognitive operating system” — a local infrastructure where humans and AI agents cohabit a shared memory layer. Every idea, image, or moment becomes storable, retrievable, and composable across modalities — forming a foundation for personal or collective synthetic cognition.