# Blockers — Impediments & Dependencies

**Last Updated:** 2025-11-21T00:00:00Z  
**Status:** 🟢 No Active Blockers

---

## Active Blockers

*(No active blockers at this time)*

---

## Resolved Blockers

| ID | Blocker | Impact | Owner | Resolution | Resolved Date |
|----|---------|--------|-------|------------|---------------|
| — | — | — | — | — | — |

---

## Potential Blockers (Watching)

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Task queue choice (Celery vs RQ) may delay worker implementation | Medium | Low | Write ADR early, run quick benchmarks | Silent Architect |
| Rerank provider selection (API vs local) affects latency SLOs | Medium | Medium | Test both options, document trade-offs in ADR | Silent Architect |
| Design tokens need validation against WCAG AA | Low | High | Run contrast checks early, adjust if needed | IKB Designer |

---

## Dependency Graph

```
Silent Architect (Architecture) → IKB Designer (API understanding)
  ↓
Silent Architect (MCP stubs) ← IKB Designer (Frontend integration)
  ↓
Integration Testing (Both agents)
```

**Critical Path:**
1. Architecture definition (SYSTEM.md, API_CONTRACTS.md)
2. Data model definition (DATA_MODEL.md)
3. Component library definition (COMPONENTS.md)
4. Implementation (parallel: backend + frontend)

**No blocking dependencies yet** — agents can work in parallel after initial architecture is defined.

---

## Escalation Path

**Level 1 (Team):** Agent self-resolves by updating documentation  
**Level 2 (Cross-Agent):** Orchestrator mediates via CONTEXT.md sync  
**Level 3 (External):** Human intervention required (e.g., API key procurement)

---

## Guidelines

### When to Log a Blocker
- Cannot proceed with task due to missing dependency
- Waiting >1 session for external input
- Technical limitation discovered (e.g., library incompatibility)

### When to Resolve a Blocker
- Dependency satisfied
- Workaround implemented
- Decision made (even if not ideal)

### When to Escalate
- Blocker persists >3 sessions
- Affects critical path
- Requires architectural change

---

**Update Frequency:** Real-time (whenever blocker encountered or resolved)  
**Owner:** Agent encountering blocker
