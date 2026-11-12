# HGB Annotation Platform

Web application for auditor annotation of HGB disclosure obligations.
Built with NiceGUI + PostgreSQL + Docker Compose + Caddy.

---

## Local Development Setup

### Prerequisites
- Docker Desktop running
- Python 3.11+ (for running import scripts outside Docker)

### 1. Configure environment

```bash
cd annotation_app
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, SECRET_KEY, DATA_ROOT
```

Generate a strong secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> **Security note — `SECRET_KEY`:** Access-code hashes are computed with
> PBKDF2-SHA256 using `SECRET_KEY` as the salt. The hashes are therefore
> deterministically tied to this key. Keep it secret and never change it
> after annotators have been created — changing it invalidates all existing
> codes. Use at least 32 random bytes (64 hex chars).

### 2. Start the database

```bash
docker compose up db -d
```

The schema (`annotation_schema.sql`) is applied automatically via
`docker-entrypoint-initdb.d/` — **but only on the very first start with an
empty Postgres data volume**. If you change the schema later, you must drop
and recreate the volume so the init script runs again:

```bash
docker compose down -v   # destroys pgdata volume — all data lost!
docker compose up db -d
```

For production, write and apply an explicit migration instead of relying on
this mechanism.

### 3. Run the import scripts

```bash
# Install deps locally (or use a venv)
pip install -r requirements.txt

# Seed test annotators (prints plaintext codes — note them down)
python -m scripts.seed_annotators

# Import obligations, companies, and annotation items
python -m scripts.import_data
```

### 4. Start the app

```bash
# Option A: directly
python -m app.main

# Option B: via Docker Compose (also starts Caddy)
docker compose up app -d
```

Open http://localhost:8080 and log in with one of the codes printed by `seed_annotators.py`.

---

## Production Deployment (Hetzner VPS)

1. SSH into the server, clone the repo
2. Copy `.env.example` → `.env`, fill in all values with production secrets
3. Edit `Caddyfile`: replace `your-domain.example.com` with the real domain
4. Set `DATA_ROOT` to the path where source files are on the server
5. `docker compose up -d`

Caddy handles TLS automatically.

### Daily Backup (pg_dump)

Add to crontab on the VPS (`crontab -e`):
```
0 3 * * * docker exec annotation_app-db-1 pg_dump -U annotation annotation | gzip > /backups/annotation_$(date +\%Y\%m\%d).sql.gz
```

---

## Milestone Status

| # | Milestone | Status |
|---|-----------|--------|
| 1 | Skeleton: login, DB connection, schema, seed | ✅ Done |
| 2 | Annotation mask (3 questions, conditional flow) | ✅ Done |
| 3 | Assignment logic (Coverage / Agreement phases) | ✅ Done |
| 4 | PDF embedding + GT context helpers | ⏳ |
| 5 | Export + admin access | ⏳ |
| 6 | Hetzner deployment config | ⏳ |
