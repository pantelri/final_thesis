# Deployment – HGB Annotation App (Hetzner, Deutschland)

Ziel: Self-Hosting auf einem Hetzner-Cloud-VPS in einem deutschen Rechenzentrum,
Datenhaltung vollständig in der EU, tägliches Backup, manueller Export jederzeit.

## 1. Server (EU-Datenhaltung)

- Hetzner Cloud, **Standort Nürnberg (`nbg1`) oder Falkenstein (`fsn1`)** – beide
  Deutschland. (Helsinki `hel1` wäre Finnland = ebenfalls EU, aber für „Daten in
  Deutschland" Nürnberg/Falkenstein wählen.)
- Empfehlung **CX22** (2 vCPU, 4 GB RAM, 40 GB SSD) – reicht für App + Postgres +
  Caddy bei wenigen parallelen Annotatoren. Bei mehr Headroom CX32.
- OS: Ubuntu 24.04 LTS.
- Kein US-Cloud-Dienst in der Kette: Postgres läuft lokal im Container, das
  PDF-/md-Volume liegt auf dem Server. **Einzige Ausnahme:** die LLM-Vorschläge
  (`too_short`-Flow) gehen an OpenRouter (außerhalb EU). Das ist optional und
  betrifft nur den eingegebenen Freitext + den angezeigten Abschnitt + das
  öffentliche Geschäftsberichts-md – **keine personenbezogenen Annotatordaten.**
  Wenn auch das in der EU bleiben soll: Feature über fehlenden
  `OPENROUTER_API_KEY` deaktiviert lassen oder auf einen EU-Anbieter (z. B.
  Mistral/Aleph Alpha) umstellen (`SUGGEST_LLM_BASE_URL`).

## 2. Grundinstallation

```bash
# als root nach erster SSH-Anmeldung
adduser deploy && usermod -aG sudo deploy
apt update && apt install -y docker.io docker-compose-v2 ufw fail2ban
systemctl enable --now docker
usermod -aG docker deploy

# Firewall: nur SSH + HTTP/HTTPS
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

SSH-Härtung: Passwort-Login aus, nur Key (`PasswordAuthentication no` in
`/etc/ssh/sshd_config`), dann `systemctl restart ssh`.

## 3. App ausrollen

```bash
sudo mkdir -p /opt/annotation_app && sudo chown deploy:deploy /opt/annotation_app
# Code dorthin bringen (git clone des Repos oder rsync des source_code-Ordners)
cd /opt/annotation_app
cp .env.example .env
# .env ausfüllen:  POSTGRES_PASSWORD (stark), SECRET_KEY (python -c "import secrets;print(secrets.token_hex(32))"),
#                  DATA_ROOT=/opt/masterarbeit/source_code, ggf. OPENROUTER_API_KEY + SUGGEST_LLM_MODEL
```

**Wichtig – Produktion ohne den Dev-Mount starten** (sonst greift
`docker-compose.override.yml` mit dem Live-Code-Mount und Auto-Reload):

```bash
docker compose -f docker-compose.yml up -d --build
```

Die Override-Datei nur lokal verwenden; auf dem Server bewusst die
`-f docker-compose.yml`-Form nehmen.

### Domain & TLS
Hast du eine Domain, zeige sie per A-Record auf die Server-IP und ersetze in
`Caddyfile` den `:80`-Block durch:

```
deine-domain.de {
    reverse_proxy app:8080
    encode zstd gzip
}
```

Caddy holt dann automatisch ein Let's-Encrypt-Zertifikat (HTTPS). Ohne Domain
bleibt `:80` (nur HTTP, für einen Test akzeptabel, für echte Annotatordaten
**Domain + HTTPS einrichten**).

## 4. Migration einspielen (bestehende DB)
Bei einer frisch erstellten DB legt `annotation_schema.sql` schon alles an.
Auf eine bereits laufende DB die nicht-destruktive Migration anwenden:

```bash
docker compose exec -T db psql -U annotation -d annotation < scripts/migrate_suggestions.sql
```

## 5. Tägliches Backup (Cron)

`scripts/backup_db.sh` macht einen gzip-`pg_dump` und rotiert nach
`RETENTION_DAYS` (Default 14).

```bash
chmod +x /opt/annotation_app/scripts/backup_db.sh
sudo mkdir -p /opt/annotation_backups && sudo chown deploy:deploy /opt/annotation_backups

# Cron des deploy-Users (crontab -e):
17 3 * * * /opt/annotation_app/scripts/backup_db.sh >> /var/log/annotation_backup.log 2>&1
```

**Off-Site:** Der wissenschaftliche Wert der Daten verlangt eine zweite Kopie
außerhalb des VPS. Optionen (alle EU):
- Hetzner **Storage Box** (Helsinki/Falkenstein) – Backup-Dir per `rsync`/`borg`
  hochladen, ans Ende von `backup_db.sh` anhängen.
- Hetzner **Cloud-Snapshots/Backups** (im Cloud-Panel aktivieren) – sichern das
  ganze Volume zusätzlich.

Manuelles Backup jederzeit: einfach `scripts/backup_db.sh` von Hand ausführen.
Zusätzlich (inhaltlich) der **CSV/ZIP-Export** im Admin-Bereich – siehe unten.

### Restore (Probe regelmäßig testen!)
```bash
gunzip -c /opt/annotation_backups/annotation_YYYYmmddTHHMMSSZ.sql.gz \
  | docker compose exec -T db psql -U annotation -d annotation
```
Ein Backup, das nie zurückgespielt wurde, ist kein Backup. Einmal testen.

## 6. Manueller Inhaltsexport
Im Browser als Admin anmelden → **Admin-Bereich → Export**:
- **Alles als ZIP** (annotations + irrelevante Sätze + zusätzliche Textstellen + README)
- oder die drei CSVs einzeln.

`pg_dump` = vollständige technische Sicherung (für Wiederherstellung).
CSV/ZIP-Export = analysefertige, flache Sicht (für Auswertung & als zweite
inhaltliche Kopie).

## 7. Updates
```bash
cd /opt/annotation_app && git pull
docker compose -f docker-compose.yml up -d --build
```
Vor jedem Update sicherheitshalber `scripts/backup_db.sh` laufen lassen.

## Update: Kontingent & Zweiturteil-Zuteilung (Sept 2026)

Keine Schemaänderung, keine Migration. Auf dem Server im Verzeichnis `annotation_app/`:

```bash
docker compose exec -T db pg_dump -U annotation -Fc annotation > backups/pre_quota_$(date +%Y%m%d_%H%M).dump
git fetch origin && git checkout feature/quota-zweiturteil && git pull
grep -q '^ANNOTATION_QUOTA=' .env || echo 'ANNOTATION_QUOTA=25' >> .env
docker compose up -d --build app
docker compose logs --tail=30 app
```

Annotatoren anlegen (Codes werden nur einmal angezeigt):

```bash
docker compose exec app python -m scripts.add_annotators Hanna Marcus Felix Jerome Richard
```

Übereinstimmung auswerten (nur erste zwei Urteile je Einheit):

```bash
docker compose exec app python -m scripts.iaa_alpha --by-rater --by-obligation --disagreements /tmp/disagreements.csv
docker compose cp app:/tmp/disagreements.csv ./disagreements.csv
```

Tests lokal: `pip install -r requirements.txt -r requirements-dev.txt && python -m pytest -q tests`
