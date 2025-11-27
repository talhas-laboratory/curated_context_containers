# Single Source of Truth — Navigation Hub

**Last Updated:** 2025-11-09

This folder is the **persistent memory substrate** for all agents across all sessions. No agent operates without reading from and writing back to this environment.

---

## Quick Start for Agents

### On Session Start
1. Read this INDEX.md for orientation
2. Read CONTEXT.md for current state
3. Read PROGRESS.md for milestone status
4. Read VISION.md for product north star
5. Navigate to your domain folder (architecture/ or design/)
6. Check work/CURRENT_FOCUS.md and work/BLOCKERS.md

### On Session End
1. Update CONTEXT.md with state changes
2. Update PROGRESS.md with milestone completion
3. Append session summary to diary/YYYY-MM-DD.md
4. Update work/CURRENT_FOCUS.md with next action
5. Update your domain documentation (architecture/ or design/)

---

## Document Map

### Core State Files
- **CONTEXT.md** — Live project state snapshot (auto-updated)
- **PROGRESS.md** — Milestone tracker + status board
- **VISION.md** — Product north star (stable, rarely changes)

### Domain Documentation

#### Architecture Domain (Silent Architect)
- **architecture/SYSTEM.md** — System architecture diagrams + dataflow
- **architecture/DATA_MODEL.md** — Schemas, contracts, data flows
- **architecture/API_CONTRACTS.md** — MCP v1 + internal service APIs
- **architecture/ADR/** — Architecture Decision Records

#### Design Domain (IKB Designer)
- **design/COMPONENTS.md** — Component library contracts
- **design/TOKENS.md** — Design tokens (color, type, spacing, motion)
- **design/PATTERNS.md** — Interaction patterns + user flows
- **design/ACCESSIBILITY.md** — a11y standards + compliance

### Work Tracking
- **work/CURRENT_FOCUS.md** — Real-time: what's being worked on now
- **work/BLOCKERS.md** — Impediments + dependencies
- **work/TECHNICAL_DEBT.md** — Known compromises + remediation plans

### Knowledge Base
- **knowledge/DECISIONS.md** — Key project decisions log
- **knowledge/LESSONS.md** — Learnings from mistakes + iterations
- **knowledge/REFERENCES.md** — External docs + resources

### Temporal Log
- **diary/** — Append-only session logs
  - YYYY-MM-DD.md format
  - TEMPLATE.md for consistent structure

---

## Navigation Patterns

### For Silent Architect (Technical Agent)
```
INDEX.md → CONTEXT.md → PROGRESS.md → VISION.md
  ↓
architecture/SYSTEM.md → DATA_MODEL.md → API_CONTRACTS.md
  ↓
work/CURRENT_FOCUS.md → work/BLOCKERS.md
  ↓
[Execute work]
  ↓
Update: CONTEXT.md, PROGRESS.md, architecture/, diary/, work/
```

### For IKB Designer (Design Agent)
```
INDEX.md → CONTEXT.md → PROGRESS.md → VISION.md
  ↓
design/COMPONENTS.md → TOKENS.md → PATTERNS.md → ACCESSIBILITY.md
  ↓
architecture/API_CONTRACTS.md (cross-reference for data constraints)
  ↓
work/CURRENT_FOCUS.md → work/BLOCKERS.md
  ↓
[Execute work]
  ↓
Update: CONTEXT.md, PROGRESS.md, design/, diary/, work/
```

### For Orchestrator
```
INDEX.md → CONTEXT.md → PROGRESS.md
  ↓
architecture/ + design/ (full scan)
  ↓
work/ (status check)
  ↓
diary/ (reflection synthesis)
  ↓
Update: CONTEXT.md (synchronization), diary/ (coordination log)
```

---

## Governance Rules

1. **Append-Only Logs:** diary/ entries cannot be overwritten, only appended
2. **Single Source:** This folder is the ONLY canonical reference
3. **No Orphaned State:** All agent state must be written back here
4. **Hash Verification:** Sessions should confirm CONTEXT.md hash before proceeding
5. **Timestamped Updates:** All diary entries and significant updates include ISO timestamps

---

## File Status Legend

| Icon | Meaning |
|------|---------|
| 🟢 | Complete and stable |
| 🟡 | In progress |
| 🔴 | Blocked or needs attention |
| ⚪ | Not started |
| 📝 | Template (needs instantiation) |

---

## Current Project Phase

**Phase 1:** MCP v1 Local Implementation  
**Status:** 🟡 In Progress  
**See:** PROGRESS.md for detailed milestones

