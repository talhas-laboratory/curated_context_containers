.PHONY: migrate smoke golden-queries

MCP_DIR ?= mcp-server
DOCKER_DIR ?= docker

migrate:
	cd $(MCP_DIR) && alembic upgrade head

smoke:
	scripts/compose_smoke_test.sh

golden-queries:
	scripts/run_golden_queries.sh
