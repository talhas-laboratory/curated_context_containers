from app.services.graph_nl2cypher import validate_cypher


def test_validate_cypher_accepts_readonly():
    cypher = "MATCH (n:LLCNode {container_id:$cid}) RETURN [] AS nodes, [] AS rel_maps LIMIT 5"
    ok, issues, diags = validate_cypher(
        cypher,
        {"node_labels": ["LLCNode"], "edge_types": ["LLCEdge"]},
        max_hops=2,
        k=5,
    )
    assert ok
    assert issues == []
    assert diags.get("validated") is True


def test_validate_cypher_rejects_writes_and_missing_limit():
    cypher = "MATCH (n:Other {container_id:$cid}) CREATE (m) RETURN n"
    ok, issues, diags = validate_cypher(
        cypher,
        {"node_labels": ["LLCNode"], "edge_types": ["LLCEdge"]},
        max_hops=2,
        k=5,
    )
    assert not ok
    assert "NL2CYPHER_INVALID" in issues
    assert diags.get("missing_limit")
    assert diags.get("blocked_pattern")
