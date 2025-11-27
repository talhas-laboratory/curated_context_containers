# Technical Debt — Known Compromises & Remediation

**Last Updated:** 2025-11-09T00:30:00Z  
**Status:** 🟢 No Technical Debt (Initial State)

---

## Purpose

This document tracks intentional compromises, shortcuts, and technical debt incurred during development. Each entry includes:
- What was compromised
- Why (context and urgency)
- Impact (system risk, maintainability cost)
- Remediation plan
- Target date for payoff

---

## Active Technical Debt

### TD-001: Frontend Tests Not Configured
**Date Incurred:** 2025-11-20  
**Category:** 🟢 Minor  
**Owner:** Frontend Implementation

**Compromise:**  
No automated tests (Jest/RTL) or E2E tests (Playwright) configured for frontend components and hooks. Storybook stories exist but no unit/integration test coverage.

**Reason:**  
Step 5 frontend build plan prioritized core functionality and UI wiring over test infrastructure. Tests are marked as optional in the acceptance checklist with rationale to be documented.

**Impact:**  
- No regression protection for component changes
- Manual testing required for each change
- Risk of breaking existing functionality during refactors

**Remediation Plan:**  
1. Set up Jest + React Testing Library
2. Add unit tests for hooks (`use-containers`, `use-search`, `use-add-to-container`)
3. Add component tests for critical UI (SearchInput, ResultItem, DocumentModal)
4. Add snapshot tests for ContainerCard, DiagnosticsRail
5. Configure Playwright for E2E smoke tests (search flow, modal interactions)
6. Add MSW (Mock Service Worker) for API mocking in tests

**Estimated Effort:** 8-12 hours  
**Target Date:** Phase 2 (before production readiness)  
**Priority:** Medium

### TD-002: E2E Not Gated in CI
**Date Incurred:** 2025-11-21  
**Category:** 🟡 Moderate  
**Owner:** Orchestrator

**Compromise:**  
Playwright E2E search script exists but CI marks it non-blocking (`continue-on-error` in workflow) and uses a dev token. Failures will not break the pipeline.

**Reason:**  
Stability risk for transient failures on shared runners; prioritizing backend smoke/golden gating first.

**Impact:**  
- UI regressions may slip if only E2E catches them.  
- Manual attention required to inspect artifacts when failures happen.

**Remediation Plan:**  
1. Harden E2E (deterministic fixtures, MSW, hosted frontend build).  
2. Make E2E step required in CI after flake rate <2%.  
3. Replace dev token with GitHub secret + env wiring.  

**Estimated Effort:** 6-8 hours  
**Target Date:** Phase 2 kickoff  
**Priority:** Medium

---

## Paid Off Technical Debt

| ID | Compromise | Reason | Impact | Remediation | Paid Date |
|----|------------|--------|--------|-------------|-----------|
| — | — | — | — | — | — |

---

## Debt Categories

### 🔴 Critical (Address Immediately)
- Security vulnerabilities
- Data loss risks
- SLO breaches

### 🟡 Moderate (Address Within Phase)
- Performance degradation
- Maintainability issues
- Missing observability

### 🟢 Minor (Address When Convenient)
- Code style inconsistencies
- Missing documentation
- Suboptimal but functional

---

## Example Entry Template

### TD-001: [Short Title]
**Date Incurred:** YYYY-MM-DD  
**Category:** 🟡 Moderate  
**Owner:** [Agent responsible]

**Compromise:**  
[What shortcut was taken or what standard was not met]

**Reason:**  
[Why this compromise was necessary — timeline, dependency, unknown]

**Impact:**  
[What is the ongoing cost — latency, bugs, confusion, maintenance burden]

**Remediation Plan:**  
1. Step 1
2. Step 2
3. Step 3

**Estimated Effort:** X hours  
**Target Date:** YYYY-MM-DD  
**Priority:** High | Medium | Low

---

## Guidelines

### When to Log Technical Debt
- Skipped tests to meet deadline
- Hardcoded values instead of config
- Skipped error handling for "happy path only"
- Used suboptimal algorithm for speed of implementation
- Left TODO comments in production code
- Skipped documentation

### When NOT to Log
- Normal refactoring opportunities (not debt, just evolution)
- Personal coding style preferences
- Disagreements on approach (resolve via ADR, not debt log)

### Payoff Strategy
- Address critical debt before new features
- Pay off at least one moderate debt per phase
- Minor debt can wait until natural refactoring opportunity

---

**Update Frequency:** When debt incurred or paid off  
**Owner:** Agent who introduced compromise or agent paying it off
