import os

# Unit tests run without a live Postgres/Qdrant/Neo4j stack. Disable automatic
# migrations on FastAPI startup so TestClient can boot the app.
os.environ.setdefault("LLC_AUTO_MIGRATE", "false")

