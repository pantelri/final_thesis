#!/usr/bin/env bash
#
# Daily PostgreSQL backup for the HGB annotation app (run via cron on the VPS).
#
# Creates a gzipped pg_dump of the annotation database inside a timestamped
# file and prunes dumps older than RETENTION_DAYS. Safe to run by hand at any
# time for a manual backup.
#
# Cron example (daily at 03:17, low-traffic):
#   17 3 * * * /opt/annotation_app/scripts/backup_db.sh >> /var/log/annotation_backup.log 2>&1
#
set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────────────
# Directory holding docker-compose.yml (the deployment root on the VPS).
APP_DIR="${APP_DIR:-/opt/annotation_app}"
# Where dumps are stored. Put this on a volume that is ITSELF backed up
# (e.g. Hetzner Storage Box / snapshot) so the dumps survive disk loss.
BACKUP_DIR="${BACKUP_DIR:-/opt/annotation_backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

# DB credentials are read from the deployment .env so they stay in one place.
set -a
# shellcheck disable=SC1091
source "${APP_DIR}/.env"
set +a
DB_NAME="${POSTGRES_DB:-annotation}"
DB_USER="${POSTGRES_USER:-annotation}"

# ── Backup ──────────────────────────────────────────────────────────────────
mkdir -p "${BACKUP_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/annotation_${STAMP}.sql.gz"
TMP="${OUT}.partial"

cd "${APP_DIR}"

# pg_dump runs inside the db container; -T = no TTY (cron has none).
# Stream straight to gzip so the dump is never written uncompressed.
docker compose exec -T db pg_dump -U "${DB_USER}" -d "${DB_NAME}" \
    | gzip -9 > "${TMP}"

# Only publish the file once the dump finished without error.
mv "${TMP}" "${OUT}"
echo "$(date -u +%FT%TZ)  backup ok: ${OUT} ($(du -h "${OUT}" | cut -f1))"

# ── Retention ───────────────────────────────────────────────────────────────
find "${BACKUP_DIR}" -name 'annotation_*.sql.gz' -mtime +"${RETENTION_DAYS}" -delete
echo "$(date -u +%FT%TZ)  pruned dumps older than ${RETENTION_DAYS} days"
