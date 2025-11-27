# Single Source of Truth — Agent Memory Environment

**Created:** 2025-11-09  
**Status:** 🟢 Operational  
**Version:** 1.0

---

## What Is This?

This folder is the **persistent memory substrate** for all AI agents working on the Local Latent Containers project. It ensures that every agent, across every session, has complete access to:

- Current project state and progress
- All architectural and design decisions
- Complete documentation and specifications
- Work tracking and blockers
- Institutional knowledge and learnings

---

## Quick Start

### For Agents

**Every session MUST:**
1. **Start** by reading `INDEX.md` → `CONTEXT.md` → `PROGRESS.md`
2. **Navigate** to your domain folder (`architecture/` or `design/`)
3. **Check** `work/CURRENT_FOCUS.md` and `work/BLOCKERS.md`
4. **Execute** your task
5. **Update** `CONTEXT.md` and `PROGRESS.md` with changes
6. **Log** session summary to `diary/YYYY-MM-DD.md`
7. **Refresh** `work/CURRENT_FOCUS.md` with next action

**Read `INDEX.md` for complete navigation guide.**

### For Humans

This folder is the **authoritative source** for all project documentation. Use it to:

- Understand current project state (`CONTEXT.md`)
- Review progress and milestones (`PROGRESS.md`)
- Understand product vision (`VISION.md`)
- Review agent session logs (`diary/`)
- Audit decisions and learnings (`knowledge/`)

---

## Folder Structure

```
single_source_of_truth/
├─ INDEX.md                  ← START HERE (navigation hub)
├─ CONTEXT.md                ← Live project state
├─ PROGRESS.md               ← Milestone tracker
├─ VISION.md                 ← Product north star
├─ README.md                 ← This file
├─ architecture/             ← Silent Architect domain
│  ├─ SYSTEM.md
│  ├─ DATA_MODEL.md
│  ├─ API_CONTRACTS.md
│  └─ ADR/                   ← Architecture Decision Records
├─ design/                   ← IKB Designer domain
│  ├─ COMPONENTS.md
│  ├─ TOKENS.md
│  ├─ PATTERNS.md
│  └─ ACCESSIBILITY.md
├─ work/                     ← Active work tracking
│  ├─ CURRENT_FOCUS.md       ← Real-time task status
│  ├─ BLOCKERS.md            ← Impediments
│  └─ TECHNICAL_DEBT.md      ← Known compromises
├─ knowledge/                ← Institutional memory
│  ├─ DECISIONS.md           ← Key decisions log
│  ├─ LESSONS.md             ← Learnings from experience
│  └─ REFERENCES.md          ← External docs
└─ diary/                    ← Session logs (append-only)
   ├─ TEMPLATE.md
   └─ YYYY-MM-DD.md
```

---

## Key Principles

### 1. Single Source of Truth
This folder is the **only** canonical reference for project state. No agent operates from memory or external state.

### 2. Read-Before-Write
Every agent session begins by reading the current state before making any changes.

### 3. Write-Back-Always
Every agent session ends by writing back all state changes, decisions, and reflections.

### 4. Append-Only Logs
Diary entries cannot be overwritten, only appended. This provides an immutable audit trail.

### 5. Clear Ownership
- **Orchestrator:** Coordination, CONTEXT.md, PROGRESS.md
- **Silent Architect:** architecture/, backend concerns
- **IKB Designer:** design/, frontend concerns

---

## Document Status Legend

| Icon | Status |
|------|--------|
| 🟢 | Complete and stable |
| 🟡 | In progress / partially defined |
| 🔴 | Blocked or needs attention |
| ⚪ | Not started |
| 📝 | Template (needs instantiation) |

---

## Current Status

**Phase:** 1 — MCP v1 Local Implementation  
**Progress:** 🟡 5% Complete  
**Foundation:** ✅ Complete (single_source_of_truth/ structure operational)

**See `PROGRESS.md` for detailed milestone status.**

---

## Governance

### Update Frequency
- **CONTEXT.md:** After every agent session
- **PROGRESS.md:** When milestones change status
- **diary/:** After every agent session (append entry)
- **work/CURRENT_FOCUS.md:** Real-time (whenever work shifts)
- **work/BLOCKERS.md:** When blockers encountered or resolved

### Validation
- All diary entries include ISO timestamps
- All decisions logged to `knowledge/DECISIONS.md`
- All ADRs follow template in `architecture/ADR/TEMPLATE.md`
- Cross-references verified (no broken links)

---

## Getting Help

**Disoriented?** Read `INDEX.md` (navigation hub)  
**Need context?** Read `CONTEXT.md` (current state)  
**What to work on?** Check `work/CURRENT_FOCUS.md`  
**Stuck?** Check `work/BLOCKERS.md`  
**Why was X decided?** Check `knowledge/DECISIONS.md` or `architecture/ADR/`

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-09 | Initial structure created | Orchestrator |

---

**Maintained By:** All Agents (Orchestrator, Silent Architect, IKB Designer)  
**Last Updated:** 2025-11-09T00:30:00Z

