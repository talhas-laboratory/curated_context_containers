# ADR-XXX: [Short Title]

**Date:** YYYY-MM-DD  
**Status:** [Proposed | Accepted | Deprecated | Superseded by ADR-YYY]  
**Deciders:** [List of people/agents involved]  
**Tags:** [architecture, performance, security, etc.]

---

## Context

[Describe the situation, problem, or opportunity that requires a decision. Include:
- What is the current state?
- What constraints exist?
- What assumptions are we making?
- What are the business/technical drivers?]

---

## Decision

[State the architectural decision clearly and concisely. This should be actionable.]

**Example:**
> We will use RQ instead of Celery for the task queue because...

---

## Rationale

[Explain WHY this decision was made. Include:
- How does it solve the problem?
- What trade-offs were considered?
- What principles guided the decision?
- What data or evidence supports this choice?]

---

## Alternatives Considered

### Option 1: [Alternative Name]
**Description:** [Brief description]  
**Pros:**
- [Advantage]
- [Advantage]

**Cons:**
- [Disadvantage]
- [Disadvantage]

**Reason for Rejection:** [Why this was not chosen]

---

### Option 2: [Alternative Name]
**Description:** [Brief description]  
**Pros:**
- [Advantage]

**Cons:**
- [Disadvantage]

**Reason for Rejection:** [Why this was not chosen]

---

## Consequences

### Positive
- [Benefit this decision enables]
- [Technical improvement]
- [Developer experience improvement]

### Negative
- [Trade-off or limitation]
- [Technical debt incurred]
- [Operational complexity added]

### Neutral
- [Side effects that are neither clearly good nor bad]

---

## Implementation Notes

**Steps Required:**
1. [Action item]
2. [Action item]
3. [Action item]

**Affected Components:**
- [List systems/modules that will change]

**Migration Strategy:**
- [If replacing an existing system, how will migration happen?]

**Rollback Plan:**
- [How to revert this decision if needed]

---

## Success Metrics

[How will we know if this decision was the right one?]

**Metrics to Track:**
- [Quantifiable metric, e.g., latency, error rate]
- [Developer productivity metric]
- [User satisfaction metric]

**Gates:**
- [Threshold for success]
- [Threshold for rollback]

---

## References

- [Link to related issue, doc, or discussion]
- [Link to relevant benchmark or research]
- [Link to proof of concept]

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| YYYY-MM-DD | Initial draft | [Name] |
| YYYY-MM-DD | Accepted after review | [Name] |

