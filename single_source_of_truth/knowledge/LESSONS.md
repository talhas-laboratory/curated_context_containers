# Lessons Learned — Retrospective Insights

**Last Updated:** 2025-11-23T15:15:00Z

---

## Purpose

This document captures learnings from mistakes, unexpected challenges, and successful patterns observed during development. Unlike DECISIONS.md (which logs choices), this document reflects on outcomes and process improvements.

---

## Lessons Log

### 2025-11-09: Comprehensive Templates Reduce Friction
**Context:** Bootstrap session creating single_source_of_truth/ structure.

**Observation:**  
Creating detailed templates upfront (TEMPLATE.md for diary, templates for ADR, API contracts, etc.) significantly reduces decision fatigue in future sessions. Agents don't have to invent structure each time.

**What Worked:**
- Templates provide clear expectations
- Consistency across sessions enforced automatically
- Examples in templates teach by showing

**What Could Improve:**
- Could add validation scripts to ensure templates are followed
- Could add automation to populate templates with metadata (timestamps, agent names)

**Application:**  
Always create templates for recurring documents (diary entries, ADRs, test reports).

**Owner:** Orchestrator

---

### 2025-11-09: Explicit Session Protocols Enforce Discipline
**Context:** Adding session initialization/closure sections to agent specs.

**Observation:**  
By encoding "read INDEX.md → read CONTEXT.md → read domain docs → execute → write back" into agent specifications, we make memory persistence automatic rather than aspirational.

**What Worked:**
- Explicit protocols reduce cognitive load ("what do I read first?")
- Checklists prevent skipped steps
- Clear termination conditions prevent premature session end

**What Could Improve:**
- Could add automated hash verification (CONTEXT.md hash check at start)
- Could add pre-flight validation (do required files exist?)

**Application:**  
Codify all critical workflows as checklists in agent specs, not just guidelines.

**Owner:** Orchestrator

---

### 2025-11-23: Golden Queries Must Mirror Fixture Vocabulary
**Context:** Expanded golden suite with PDF and latency/no-hit cases.

**Observation:**  
Golden runs returned `NO_HITS` until queries were rephrased to match seeded text; judgments also needed to point at actual doc_ids.

**What Worked:**
- Aligning query wording to fixture vocabulary unlocked hits immediately.
- Mapping judgments to real doc_ids restored meaningful nDCG/recall.

**What Could Improve:**
- Add guardrails in `run_golden_queries.sh` to compute nDCG/recall automatically and flag queries with zero tsquery overlap.

**Application:**  
When fixtures are synthetic, keep golden queries lexically close to the seed content and refresh judgments after ingestion.

**Owner:** Silent Architect

---

### 2025-11-09: Navigation Hub (INDEX.md) Reduces Disorientation
**Context:** Creating INDEX.md as entry point for all agents.

**Observation:**  
New agents (or agents after long gaps) benefit enormously from a single "start here" document that maps the entire documentation landscape. Reduces time spent searching.

**What Worked:**
- Quick Start for Agents section provides immediate orientation
- Document Map with descriptions clarifies purpose
- Navigation Patterns show recommended reading order

**What Could Improve:**
- Could add visual diagram (ASCII art) of folder structure
- Could add "last modified" timestamps per document

**Application:**  
Always provide a README-style hub at the root of any complex documentation system.

**Owner:** Orchestrator

---

### 2025-11-27: Systematic Troubleshooting Pattern for Full-Stack Issues
**Context:** Frontend redesign + upload status bar implementation with multiple integration failures.

**Observation:**  
When facing connection/integration issues across frontend/backend/Docker stack, a systematic debugging approach significantly reduces time to resolution. Following a checklist prevents jumping to conclusions.

**What Worked:**
- **Layered debugging:** Start with browser console → backend logs → config files → direct API tests → container inspection
- **Isolation testing:** Use `curl` to test endpoints directly, removing frontend variables
- **Explicit over implicit:** When browser defaults fail (form submit, localhost resolution), add explicit handlers
- **Container awareness:** Remember that Docker volume mounts don't auto-sync new files—rebuild required
- **IPv4/IPv6 clarity:** Use `127.0.0.1` instead of `localhost` on macOS to avoid ambiguity

**Troubleshooting Checklist Applied:**
1. Check browser console for client-side errors
2. Check backend logs (`docker logs <container>`) for server-side errors
3. Verify environment variables and configuration files exist and are loaded
4. Test API endpoints with `curl` to isolate frontend vs backend
5. Inspect Docker container filesystem to verify code changes are present
6. Rebuild containers when adding new files (not just editing existing ones)
7. Add console logging to trace execution flow when behavior is unclear
8. Replace implicit browser behavior with explicit event handlers when needed

**What Could Improve:**
- Could create a troubleshooting runbook with this checklist
- Could add health check endpoints that verify all config/env vars are loaded
- Could add startup validation that fails fast if required files are missing

**Application:**  
When debugging full-stack issues, follow the layered approach and test each layer independently before assuming the problem is elsewhere. Document the pattern for future sessions.

**Owner:** Orchestrator

---

## Patterns Observed

### Successful Patterns
1. **Single Source of Truth:** Folder-based persistent memory prevents state fragmentation
2. **Append-Only Logs:** Immutable history (diary/) provides audit trail without risk of data loss
3. **Separation of Concerns:** Domain folders (architecture/, design/) clarify ownership
4. **Templates:** Reduce decision fatigue and enforce consistency
5. **Checklists:** Explicit workflows (session init/closure) prevent skipped steps

### Anti-Patterns to Avoid
1. **Scattered State:** Storing state in multiple places (git history, external DB, in-memory) causes desync
2. **Implicit Protocols:** Relying on agent "remembering" to update docs leads to stale state
3. **Flat Structure:** Mixing all docs in one folder creates navigation overhead
4. **Vague Ownership:** Unclear who maintains what leads to orphaned docs

---

## Process Improvements

### Implemented
- Session diary template with reflection prompts
- Explicit session initialization/closure in agent specs
- INDEX.md as navigation hub
- Four-tier documentation structure (state/domain/work/knowledge)

### Proposed (Not Yet Implemented)
- Automated CONTEXT.md hash computation
- Pre-flight validation script (check required files exist)
- Post-session validation script (ensure write-back happened)
- Automated PROGRESS.md updates from diary logs

---

## Mistakes Made

### 2025-11-09: None Yet
*(First session, no mistakes logged yet)*

---

## Retrospective Themes

*(To be populated after each phase completion)*

---

**Update Frequency:** After each session or phase retrospective  
**Owner:** Any agent reflecting on learnings
