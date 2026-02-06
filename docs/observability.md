# Observability (Prometheus + Grafana + Loki)

This stack is optional and designed for the single-host production compose setup.

## Start

```bash
docker compose -f docker/compose.prod.yaml -f docker/compose.observability.yaml up -d
```

## Access

- Prometheus: `http://<host>:9090`
- Grafana: `http://<host>:3001` (default user: `admin`, password: `GRAFANA_ADMIN_PASSWORD`)
- Loki: `http://<host>:3100`

## Metrics & Logs

Prometheus scrapes:
- MCP: `/metrics`
- Qdrant: `/metrics`
- MinIO: `/minio/v2/metrics/cluster`
- Neo4j: `/metrics` (Prometheus enabled via env)
- Postgres exporter: `postgres-exporter:9187`
- Node exporter: `node-exporter:9100`

MinIO metrics are exposed with `MINIO_PROMETHEUS_AUTH_TYPE=public` on the internal network.

Promtail ships Docker logs into Loki.

## Alerts

Alert rules are defined in `docker/observability/alert.rules.yml`:
- Service down
- MCP search error spike
- Backup stale/missing (driven by `llc_backup_last_success_timestamp`)

## Backup Metric

The backup script writes a Prometheus textfile metric to `/srv/llc/metrics/llc_backup.prom`.
Ensure backups run on schedule so the alert stays green.
