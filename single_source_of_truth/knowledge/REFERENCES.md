# External References — Resources & Documentation

**Last Updated:** 2025-11-09T00:30:00Z

---

## Purpose

This document collects links to external documentation, research papers, benchmarks, and tools referenced during the project.

---

## Technology Stack References

### Backend

#### FastAPI
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [OpenAPI Specification](https://swagger.io/specification/)

#### Databases
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant HNSW Configuration](https://qdrant.tech/documentation/guides/configuration/)

#### Task Queues
- [Celery Documentation](https://docs.celeryproject.org/)
- [RQ (Redis Queue) Documentation](https://python-rq.org/)
- [Comparison: Celery vs RQ](https://www.fullstackpython.com/celery.html)

#### Object Storage
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [S3 API Compatibility](https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html)

### Frontend

#### React & Next.js
- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [React Hooks Reference](https://react.dev/reference/react)

#### Styling & Animation
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Framer Motion Documentation](https://www.framer.com/motion/)
- [CSS Custom Properties (Variables)](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)

#### State Management
- [React Context API](https://react.dev/reference/react/useContext)
- [Zustand Documentation](https://zustand-demo.pmnd.rs/)

### Infrastructure

#### Docker
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Volumes](https://docs.docker.com/storage/volumes/)
- [Docker Networking](https://docs.docker.com/network/)

#### Observability
- [Prometheus Documentation](https://prometheus.io/docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Structured Logging Best Practices](https://www.structlog.org/)

---

## Embeddings & Retrieval

### Nomic Embed
- [Nomic Embed Documentation](https://docs.nomic.ai/reference/endpoints/embed)
- [nomic-embed-multimodal-7b Model Card](https://huggingface.co/nomic-ai/nomic-embed-multimodal-v7b)

### Retrieval Algorithms
- [Reciprocal Rank Fusion (RRF)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [HNSW Algorithm Paper](https://arxiv.org/abs/1603.09320)
- [BM25 Ranking Function](https://en.wikipedia.org/wiki/Okapi_BM25)

### Reranking
- [Cohere Rerank Documentation](https://docs.cohere.com/reference/rerank)
- [Cross-Encoders for Reranking](https://www.sbert.net/examples/applications/cross-encoder/README.html)

---

## Design & Accessibility

### Design Systems
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Material Design (for reference, not adoption)](https://m3.material.io/)

### Accessibility
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [VoiceOver Guide (macOS)](https://support.apple.com/guide/voiceover/welcome/mac)
- [NVDA Screen Reader](https://www.nvaccess.org/)

### Typography
- [Butterick's Practical Typography](https://practicaltypography.com/)
- [The Elements of Typographic Style](https://en.wikipedia.org/wiki/The_Elements_of_Typographic_Style)

### Color & Contrast
- [International Klein Blue (IKB)](https://en.wikipedia.org/wiki/International_Klein_Blue)
- [Color Contrast Analyzer](https://www.tpgi.com/color-contrast-checker/)

---

## Evaluation & Metrics

### Information Retrieval Metrics
- [nDCG (Normalized Discounted Cumulative Gain)](https://en.wikipedia.org/wiki/Discounted_cumulative_gain)
- [Precision and Recall](https://en.wikipedia.org/wiki/Precision_and_recall)
- [Mean Reciprocal Rank (MRR)](https://en.wikipedia.org/wiki/Mean_reciprocal_rank)

### Latency & Performance
- [Percentile Latency (P50, P95, P99)](https://www.brendangregg.com/blog/2020-11-08/heatmaps.html)
- [Service Level Objectives (SLOs)](https://sre.google/sre-book/service-level-objectives/)

---

## MCP (Model Context Protocol)

- [MCP Specification (Anthropic)](https://modelcontextprotocol.io/)
- [MCP GitHub Repository](https://github.com/modelcontextprotocol)
- [MCP Servers List](https://github.com/modelcontextprotocol/servers)

---

## Research Papers

### Vector Search
- [Efficient and Robust Approximate Nearest Neighbor Search](https://arxiv.org/abs/1603.09320) (HNSW)
- [FAISS: A Library for Efficient Similarity Search](https://arxiv.org/abs/1702.08734)

### Embeddings
- [BERT: Pre-training of Deep Bidirectional Transformers](https://arxiv.org/abs/1810.04805)
- [Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks](https://arxiv.org/abs/1908.10084)

### Retrieval
- [Dense Passage Retrieval for Open-Domain Question Answering](https://arxiv.org/abs/2004.04906)
- [Hybrid Search: Combining Lexical and Semantic Search](https://arxiv.org/abs/2104.08663)

---

## Tools

### Development
- [Ruff (Python Linter)](https://docs.astral.sh/ruff/)
- [Black (Python Formatter)](https://black.readthedocs.io/)
- [mypy (Static Type Checker)](https://mypy.readthedocs.io/)

### Testing
- [pytest Documentation](https://docs.pytest.org/)
- [Cypress E2E Testing](https://www.cypress.io/)
- [Playwright](https://playwright.dev/)

### Version Control
- [Git Best Practices](https://git-scm.com/book/en/v2)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## Inspiration & Philosophy

### Design Philosophy
- [Dieter Rams: 10 Principles of Good Design](https://www.vitsoe.com/us/about/good-design)
- [Calm Technology](https://calmtech.com/)
- [Design Justice Principles](https://designjustice.org/read-the-principles)

### Systems Thinking
- [The Mythical Man-Month](https://en.wikipedia.org/wiki/The_Mythical_Man-Month) (Fred Brooks)
- [A Philosophy of Software Design](https://web.stanford.edu/~ouster/cgi-bin/book.php) (John Ousterhout)

---

**Update Frequency:** When new references added during research  
**Owner:** Any agent discovering useful resources

