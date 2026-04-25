#!/bin/bash
# .agent/refresh.sh — Self-Healing MANIFEST.json updater
# Run manually or add to cron to keep MANIFEST.json current.
# Usage: bash /root/.openclaw/.agent/refresh.sh

set -e
MANIFEST="/root/.openclaw/.agent/MANIFEST.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
PGPASS="pxQSY8IjfYEsiBSd42e6ke+h4tmO1eFU705sLqYHJEU="

echo "[$TIMESTAMP] Starting MANIFEST refresh..."

# --- 1. Refresh DB table list + sizes ---
echo "  Querying DB schema..."
DB_SNAPSHOT=$(PGPASSWORD="$PGPASS" psql -h 127.0.0.1 -U tcginvest -d tcginvest -t -A -F'|' \
  -c "SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name))), \
      (SELECT COUNT(*) FROM information_schema.columns WHERE table_name=t.table_name AND table_schema='public') \
      FROM information_schema.tables t WHERE table_schema='public' ORDER BY table_name;" 2>&1)

echo "  DB tables found:"
echo "$DB_SNAPSHOT" | while IFS='|' read -r tname tsize tcols; do
  echo "    - $tname ($tsize, $tcols cols)"
done

# --- 2. Refresh cron inventory ---
echo "  Reading cron jobs..."
CRON_JOBS=$(cat /etc/cron.d/tcginvest 2>/dev/null | grep -v '^#' | grep -v '^$' | grep -v '^SHELL' | grep -v '^PATH')

# --- 3. Update meta.generated_at in MANIFEST.json ---
python3 << PYEOF
import json, subprocess, datetime

with open('$MANIFEST', 'r') as f:
    manifest = json.load(f)

# Update timestamp
manifest['meta']['generated_at'] = '$TIMESTAMP'
manifest['meta']['last_refresh'] = '$TIMESTAMP'

# Refresh DB table sizes from live query
result = subprocess.run(
    ['psql', '-h', '127.0.0.1', '-U', 'tcginvest', '-d', 'tcginvest', '-t', '-A', '-F', '|',
     '-c', """SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name))),
              (SELECT COUNT(*) FROM information_schema.columns 
               WHERE table_name=t.table_name AND table_schema='public')
              FROM information_schema.tables t WHERE table_schema='public' ORDER BY table_name;"""],
    capture_output=True, text=True,
    env={**__import__('os').environ, 'PGPASSWORD': '$PGPASS'}
)

for line in result.stdout.strip().split('\n'):
    parts = line.strip().split('|')
    if len(parts) == 3:
        tname, tsize, tcols = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if tname in manifest['database']['tables']:
            manifest['database']['tables'][tname]['size'] = tsize
            manifest['database']['tables'][tname]['columns'] = int(tcols) if tcols.isdigit() else manifest['database']['tables'][tname].get('columns')

with open('$MANIFEST', 'w') as f:
    json.dump(manifest, f, indent=2)

print("  MANIFEST.json updated with latest DB sizes.")
PYEOF

echo "[$TIMESTAMP] Refresh complete. MANIFEST.json is current."
