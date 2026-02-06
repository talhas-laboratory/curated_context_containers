# Backup & Restore (Single Host)

These scripts are intended for the production Compose stack on a single host.

## Backup

Create a full backup set (Postgres dump + volume tarballs):

```bash
BACKUP_ROOT=/srv/llc/backups \
STOP_SERVICES=1 \
./scripts/backup_prod.sh
```

Notes:
- `STOP_SERVICES=1` stops Qdrant/MinIO/Neo4j during volume tar to improve consistency.
- Backups are stored under `$BACKUP_ROOT/<timestamp>`.

## Restore

Restore from a backup directory (destructive):

```bash
RESTORE_FORCE=1 \
STOP_SERVICES=1 \
RESET_DB=1 \
./scripts/restore_prod.sh /srv/llc/backups/<timestamp>
```

Notes:
- `RESTORE_FORCE=1` is required to prevent accidental restores.
- `RESET_DB=1` drops and recreates the `public` schema before restoring.
- Restore overwrites `/srv/llc/qdrant`, `/srv/llc/minio`, and `/srv/llc/neo4j`.

## Scheduling (Cron)

Example daily backup at 2:00 AM with 14-day retention:

```bash
0 2 * * * BACKUP_ROOT=/srv/llc/backups RETENTION_DAYS=14 /srv/llc/curated_context_containers/scripts/backup_prod.sh >> /var/log/llc-backup.log 2>&1
```

To install, add the line to the host crontab (`crontab -e`).

## Retention & Verification

Environment variables:
- `RETENTION_DAYS` (default 14)
- `RETENTION_COUNT` (optional, keeps newest N)
- `VERIFY` (default 1, validates archives and non-empty SQL)

## Backup Metric

Backups write a Prometheus textfile metric to `METRICS_DIR` (default: `/srv/llc/metrics`).
This powers the backup freshness alert in the observability stack.
