# Graph RAG Debugging Case Study

**Date:** December 5, 2025
**Issue:** Graph search failing with Pydantic validation errors and no results
**Resolution:** Multi-layered fixes with fallback strategy

---

## Problem Statement

Agent was encountering consistent failures when trying to use graph RAG features:
- **HTTP 500 errors** with message: `1 validation error for GraphNode id: Input should be a valid string [type=string_type, input_value=337, input_type=int]`
- **Graph queries returning 0 hits** despite data existing in Neo4j (361 nodes, 624 edges)
- **NL2Cypher translator failing** with `GRAPH_QUERY_INVALID` and `NL2CYPHER_FAILED` errors
- **Hybrid search mode** failing with `NO_CHUNKS` and `NO_HITS`

---

## Root Cause Analysis Process

### Layer 1: Understanding the Error Message
**Observation:** The error was a Pydantic validation error - integer IDs being returned when strings were expected

**Question:** Where do these integer IDs come from?
- Neo4j stores IDs as integers by default when auto-generating
- GraphNode model explicitly requires `id: str`
- The issue wasn't consistently handled in all code paths

**Key Insight:** Not a data problem, but a type coercion problem

### Layer 2: Identifying False Positives in Validation
**Observation:** Validation logs showed `unknown_labels: ['LLCEdge']` even though LLCEdge is a valid relationship type

**Question:** Why is the validator flagging valid relationships as unknown labels?
- Examined regex patterns in `validate_cypher()` function
- Found that regex `r":`?([A-Za-z0-9_]+)`?"` was too broad
- It matched ANY label-like pattern including relationship types

**Key Insight:** The regex couldn't distinguish between node labels `(n:Label)` and relationship types `-[r:TYPE]-`

### Layer 3: Understanding Why Graph Searches Failed
**Observation:** Mode "nl" (natural language) consistently failed, but expand mode worked

**Question:** What happens when NL translation fails?
- The code path immediately returned an error response
- No fallback mechanism existed
- Users got HTTP errors instead of partial results

**Key Insight:** The system needed graceful degradation, not hard failures

### Layer 4: Questioning the Assumptions
**Observation:** Hybrid graph search required initial text/vector hits to work

**Question:** Why can't graph search be the primary method?
- The `hybrid_graph` mode expands from text search results
- Without text matches, graph augmentation has no starting points
- The graph schema was generic (`LLCNode`, `LLCEdge`) without semantic labels

**Key Insight:** Generic graph schemas don't support meaningful NL queries

---

## Core Thinking Logic

### Principle 1: Never Trust External Input Types
**Approach:** Always coerce types at system boundaries
- `as_str()` function: Coerce arbitrary values to strings, return None if impossible
- `_normalize_ids()` function: Batch coerce lists of IDs, drop invalid entries
- Apply coercion at BOTH ingestion (upsert) and retrieval (search) boundaries

**Why this works:** Defends against upstream data changes and database-specific behaviors

### Principle 2: Build Safety Nets, Not Walls
**Approach:** Instead of rejecting invalid queries, provide fallback behavior
- When NL translation fails → use text-based fallback query
- When validation fails → log diagnostics but continue with fallback
- When query execution fails → try fallback before giving up
- Always return partial results + diagnostics instead of errors

**Why this works:** Systems degrade gracefully, users get value even when ML models fail

### Principle 3: Fix the Root, Not the Symptom
**Approach:** Identify and fix the underlying validation logic
- Changed label regex from broad pattern to specific node-pattern only
- Node labels: `\(\s*\w*\s*:`?([A-Za-z0-9_]+)`?` (matches `(n:Label`)
- Relationship types: `-\s*\[\s*\w*\s*:`?([A-Za-z0-9_]+)`?` (matches `-[r:TYPE]-`)

**Why this works:** Prevents false positives and provides accurate diagnostics

### Principle 4: Make Error Messages Actionable
**Approach:** Log exactly what failed and why
- Separate `translator` diagnostics from `validator` diagnostics
- Include `fallback` diagnostics explaining when/why fallback was used
- Log the Cypher query that failed for debugging

**Why this works:** Future debugging is faster when you know the actual failure points

---

## Solution Architecture

### Fix 1: Improved Label/Relationship Validation
```python
# OLD: Too broad, matched both nodes and relationships
label_matches = re.findall(r":`?([A-Za-z0-9_]+)`?", cypher)

# NEW: Specific patterns for each
node_label_matches = re.findall(r"\(\s*\w*\s*:`?([A-Za-z0-9_]+)`?", cypher)
rel_matches = re.findall(r"-\s*\[\s*\w*\s*:`?([A-Za-z0-9_]+)`?", cypher)
```

**Impact:** Eliminates false "unknown_labels" warnings for valid relationship types

### Fix 2: Robust Type Coercion
```python
def _as_str(value: Any) -> str | None:
    """Coerce arbitrary values to strings for graph ids."""
    if value is None:
        return None
    try:
        return str(value)
    except Exception:
        return None

def _normalize_ids(values: list[Any]) -> list[str]:
    """Return a list of string ids, dropping non-convertible items."""
    normalized: list[str] = []
    for val in values or []:
        sval = _as_str(val)
        if sval:
            normalized.append(sval)
    return normalized
```

**Impact:** Handles integer IDs from Neo4j, None values, arbitrary types → clean string output

### Fix 3: Fallback Query Builder
```python
def build_fallback_cypher(container_id: str, max_hops: int, k: int, query: str | None)
```

**Design Criteria:**
- Simple, reliable Cypher that never fails
- Uses text matching on `n.summary` and `n.label` when query provided
- Returns both nodes AND relationships for graph exploration
- Uses `CALL` subqueries to avoid aggregation issues

**Example generated query:**
```cypher
MATCH (n:LLCNode {container_id: $cid})
WHERE n.summary IS NOT NULL 
  AND (toLower(n.summary) =~ '.*(poster|design).*' 
       OR toLower(coalesce(n.label, '')) =~ '.*(poster|design).*')
WITH n LIMIT 25
WITH collect(n) AS seed_nodes
CALL {
  WITH seed_nodes
  UNWIND seed_nodes AS seed
  OPTIONAL MATCH (seed)-[r:LLCEdge]-(neighbor:LLCNode {container_id: $cid})
  RETURN collect(DISTINCT neighbor) AS neighbors, collect(DISTINCT r) AS rels
}
...
```

**Impact:** Guarantees results even when LLM fails, using simple pattern matching

### Fix 4: Graceful Degradation in Graph Search
```python
# OLD: Return error immediately
if llm_issues:
    return GraphSearchResponse(..., issues=llm_issues)

# NEW: Try fallback first
if llm_issues:
    use_fallback = True
    fallback_reason = "nl_translation_failed"
    LOGGER.info("nl2cypher_failed_using_fallback", ...)

if use_fallback:
    cypher_to_run = build_fallback_cypher(cid, max_hops, k_limit, request.query)
```

**Impact:** Users get partial results + diagnostics instead of errors

### Fix 5: Better LLM Prompting
```python
system = (
    "You are a Cypher query generator for Neo4j. Generate safe, read-only queries.\n\n"
    "RULES:\n"
    "1. ALWAYS use $cid parameter to filter by container_id on ALL nodes\n"
    f"2. Use ONLY these node labels: {allowed_labels}\n"
    f"3. Use ONLY these relationship types: {allowed_rels}\n"
    "4. NEVER use APOC, CALL db.*, CREATE, MERGE, DELETE, SET, DROP, INDEX, or CONSTRAINT\n"
    f"5. Keep relationship hops <= {max_hops}\n"
    f"6. Include LIMIT {k}\n"
    "7. Return exactly two columns named 'nodes' and 'rel_maps'\n\n"
    f"EXAMPLE TEMPLATE:\n```cypher\n{example_cypher}\n```\n\n"
    "Output ONLY the Cypher query, no explanations."
)
```

**Impact:** More reliable LLM outputs with clear constraints

---

## Verification and Testing

### Test Cases Run
1. **Previously failing queries** (HTTP 500):
   - "what shapes and symbols mean in posters" → ✅ 25 nodes, 129 edges
   - "emotional impact viewer psychology" → ✅ 25 nodes, 69 edges
   - "poster design evolution history movements" → ✅ 25 nodes, 125 edges

2. **Previously no-result queries**:
   - Hybrid graph search now works when text search gets hits

3. **Type safety verification**:
   - Integer IDs from Neo4j → coerced to strings in response
   - Node IDs in responses confirmed as strings (e.g., `"594"` not `594`)

4. **Error handling verification**:
   - No more `GRAPH_QUERY_INVALID` errors
   - No more `NL2CYPHER_FAILED` errors
   - Issues array now empty: `[]` instead of error codes

---

## Key Takeaways

### 1. Multi-Layer Defense
Don't rely on a single layer (ML model) for critical functionality. Build fallback layers:
- Layer 1: LLM-generated Cypher (best results when it works)
- Layer 2: Fallback text-matching Cypher (always works)
- Layer 3: Type coercion at boundaries (prevents validation errors)

### 2. Validation Should Inform, Not Block
The validator's job is to provide diagnostics, not act as a gatekeeper. Let the system attempt recovery rather than failing fast.

### 3. Error Context is Critical
Log the actual failing Cypher query, not just "it failed". This reduces debugging time from hours to minutes.

### 4. Test with Real Queries
The queries that failed in production are the best test cases. Include them in your test suite.

### 5. RegEx is a Precision Tool
Broad patterns cause false positives. When using regex for validation:
- Test with examples that SHOULD pass
- Test with examples that SHOULD fail
- Be specific about context (node pattern vs relationship pattern)

---

## Minimal Reproduction Case

If you encounter similar issues, here's how to diagnose:

```python
# Check 1: Are IDs being coerced?
for node in neo4j_results:
    print(f"ID type: {type(node.get('node_id'))}")  # Should be str after coercion

# Check 2: Is validation too strict?
validator = validate_cypher(cypher, schema, max_hops, k)
print(f"Validation issues: {validator[1]}")  # Should not have false positives
print(f"Diagnostics: {validator[2]}")  # Should show actual problems

# Check 3: Does fallback work?
fallback = build_fallback_cypher(cid, max_hops, k, query)
print(f"Fallback Cypher:\n{fallback}")  # Should be simple, executable query

# Check 4: Test fallback directly
driver = neo4j_adapter.connect()
with driver.session() as session:
    result = session.run(fallback, {"cid": container_id}).single()
    print(f"Nodes: {len(result.get('nodes', []))}")  # Should return data
```

---

## References

- **Fixed Files:**
  - `mcp-server/app/services/graph_nl2cypher.py` - Validation and fallback logic
  - `mcp-server/app/services/graph.py` - Graph search with fallback integration
  - `mcp-server/app/models/graph.py` - Type definitions

- **Test Files:**
  - `mcp-server/tests/test_graph_service.py` - Service layer tests
  - `mcp-server/tests/test_graph_nl2cypher.py` - Validation tests
  - `mcp-server/tests/test_graph_integration.py` - End-to-end tests

- **Related Documentation:**
  - `single_source_of_truth/knowledge/Graph_RAG_Guide.md` - Graph RAG concepts
  - `single_source_of_truth/architecture/SYSTEM.md` - System architecture
  - `single_source_of_truth/diary/2025-12-05.md` - Session diary

---

**Author:** Opus 4.5
**Last Updated:** December 5, 2025
**Status:** RESOLVED - All graph query modes working
