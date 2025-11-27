# Runbook — Backup & Restore

Purpose: Preserve and recover MCP state for containers, chunks, and artifacts across Postgres, Qdrant, and MinIO.

---

## Postgres (registry + BM25)

### Backup
```bash
export LLC_POSTGRES_DSN=postgresql://local:localpw@localhost:5433/registry
pg_dump -Fc "$LLC_POSTGRES_DSN" > backups/postgres_registry.dump
```

### Restore
```bash
createdb -h localhost -p 5433 -U local registry || true
pg_restore -c -d "$LLC_POSTGRES_DSN" backups/postgres_registry.dump
```

Notes:
- Include schema + data; BM25 tsvector triggers are in the schema.
- Run `./scripts/bootstrap_db.sh` after restore if you need to reset seed container only.

## Qdrant (vector store)

### Backup snapshot
```bash
# Per collection (container) snapshot
curl -X POST http://localhost:6333/collections/c_00000000-0000-0000-0000-000000000001/snapshots
# List snapshots
curl http://localhost:6333/collections/c_00000000-0000-0000-0000-000000000001/snapshots
# Download snapshot file (adjust snapshot name)
curl -o backups/qdrant-c1.snapshot \
  http://localhost:6333/collections/c_00000000-0000-0000-0000-000000000001/snapshots/<snapshot-name>
```

### Restore
```bash
curl -X POST \
  -F "snapshot=@backups/qdrant-c1.snapshot" \
  http://localhost:6333/collections/c_00000000-0000-0000-0000-000000000001/snapshots/upload
```
When using docker volumes, you can also keep a copy of `/qdrant/storage` for disaster recovery.

## MinIO (raw documents)

### Backup (mirror to disk)
```bash
mc alias set local http://localhost:9000 localminio localminio123
mc mirror local/containers backups/minio-containers
```

### Restore
```bash
mc alias set local http://localhost:9000 localminio localminio123
mc mirror backups/minio-containers local/containers
```

Notes:
- Bucket name defaults to `containers`. Adjust if `LLC_MINIO_BUCKET` changes.
- For cold storage, tar the mirrored directory.

## Combined Recovery Order
1) Restore Postgres (schema + data).  
2) Restore MinIO bucket (raw docs).  
3) Restore Qdrant collections (vectors).  
4) Run smoke (`make smoke`) to verify search returns hits and diagnostics have timings.
