# Guide — How to Write Execution-Proof Build Plans

Purpose: A meta-spec for agents to produce build plans that are precise enough to execute blindly without gaps, drift, or ambiguity. Use this guide before drafting or refining any plan (e.g., STEP5_FRONTEND_BUILDPLAN). Copy its structure and checks into future plans.

---

## Principles
- **Contract-first:** Always anchor tasks to concrete API routes, payloads, response shapes, and schemas. No “call search API” — say `/v1/search` with exact req/resp fields.
- **Page/flow blueprints:** Describe what each page/flow does, which data it loads, how user actions map to requests, and the state machine (loading/error/success/empty/partial).
- **Wiring over widgets:** Components listed must include how they compose (props, state linkage, event handlers). Avoid “use X component” without wiring instructions.
- **A11y/keyboard explicit:** Specify keybindings, focus targets, aria roles/labels, focus traps, reduced-motion handling. Don’t leave behaviors implied.
- **Acceptance scenarios:** For every feature, define at least one acceptance test/use case with inputs and expected outputs/UX. Prefer MSW-backed Storybook/tests for UI; pytest/Playwright for E2E.
- **Parity checks:** Add checklists to verify type/contract fidelity with backend schemas and routes. Include “diff your TS types vs API_CONTRACTS” prompts.
- **Config clarity:** Document env vars, fallbacks, token/base URL resolution, and error UX when missing/misconfigured.
- **Scope decisions:** If something is optional/deferred, say so and provide a stub path or a TODO with owner. No vague “optional” without an outcome.

---

## Template for a High-Fidelity Build Plan

1) **Context & References**
   - Link to API contracts, design tokens, existing components/hooks, and relevant env vars.
   - List target routes and expected request/response schemas (inline).

2) **API Integration Tasks (per route)**
   - Route/path: `/v1/search`
   - Request DTO: fields + types + defaults
   - Response DTO: required fields (`version`, `request_id`, `partial`, `timings_ms`, `issues`, etc.)
   - Error handling: how to surface `issues`/HTTP errors in UI and logs

3) **Client/Hook Layer**
   - For each hook: name, route, request shape, response shape, caching/staleTime, retries, error mapping.
   - Example: `useSearch` POST `/v1/search` with `{query, container_ids, mode, k, diagnostics}`; expose `data, isLoading, isError, refetch`.
   - Token/base URL resolution order and header formation.

4) **Page/Flow Blueprint (per page)**
   - Data preloads (queries) and when they fire.
   - Component tree: which components render, what props they receive, how state is passed.
   - User actions → side effects: submit search, open modal, switch mode, paginate/filter.
   - States: loading, empty, error, success, partial (latency budget), no-hits, unauthorized.

5) **Components Wiring**
   - For each component: required props, events, and where it’s used.
   - Example: `ResultItem` receives `SearchResult`, `onSelect`; `DiagnosticsRail` receives `timings_ms`, `issues`, `partial`, `latency_budget`.
   - Modal wiring: open/close triggers, focus trap, escape/overlay handling, data shown (provenance, storage URI).

6) **A11y & Keyboard**
   - Keymap: `/` focus search, arrows move selection, Enter opens modal, Esc clears/close, Tab order expectations.
   - Roles/labels: `role="button"` on cards, `role="dialog" aria-modal="true"` on modal, aria-labels for inputs/buttons.
   - Reduced motion: which animations disable under `prefers-reduced-motion`.

7) **Acceptance Scenarios**
   - At least one scenario per feature with inputs/expected outputs.
   - Example: “POST `/v1/search` with container X, expect `returned>=1`, `diagnostics.timings_ms` present, `issues` empty; UI shows diagnostics rail timing badges and no-hits pill when applicable.”
   - Include MSW handlers or Playwright steps if applicable.

8) **Testing/Storybook Tasks**
   - Unit/RTL/Storybook stories per component/hook with mocked data.
   - Contract parity check: ensure TS types align with backend schemas (`version/request_id/partial/timings_ms/issues`).
   - Add commands to run (e.g., `npm test`, `npm run storybook`) and how to set env for mocks.

9) **Config & DX**
   - Env vars with defaults: `NEXT_PUBLIC_MCP_BASE_URL`, `NEXT_PUBLIC_MCP_TOKEN`.
   - Dev instructions: how to run against `make smoke` stack, how to set token, how to see request IDs.
   - Error UX if token missing/invalid.

10) **Done Criteria (checklist)**
   - Feature-level checks (routes wired, pages render, a11y behaviors verified).
   - Tests/stories executed and green (or deferred with rationale recorded in TECHNICAL_DEBT.md).
   - Manual validation steps (e.g., run against live stack, verify diagnostics rail shows timings/issues).

---

## Common Pitfalls to Avoid (from prior miss)
- Forgetting to create the actual page/route (e.g., `/containers/[id]/search`) while listing components.
- Using wrong endpoints (`/v1/containers/search` vs `/v1/search`) or omitting required response fields.
- Leaving keyboard/a11y behaviors as vague “add keyboard nav” without specific key actions.
- Not specifying how components connect to hooks, leaving unused components.
- Omitting acceptance scenarios and MSW-backed stories/tests to prove wiring.

---

## How to Use This Guide
1. Start every build plan by filling out sections 1–10 above.
2. Inline the exact DTOs and routes; copy from API_CONTRACTS.md to avoid drift.
3. Add at least one acceptance scenario and one test/story task per feature.
4. Add a final “Done Criteria” checklist; do not mark tasks complete without evidence.
5. If deferring any item, note it as TODO with owner and rationale; update TECHNICAL_DEBT.md.

Following this template should eliminate ambiguity and prevent the gaps seen in prior Step 5 planning.***
