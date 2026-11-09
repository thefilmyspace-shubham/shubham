#!/usr/bin/env bash
# Applies supabase/migrations to a throwaway local Postgres (with a small
# Supabase shim) and runs the checks in scripts/sql/checks.sql.
# Needs Postgres 15+ binaries.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PGBIN="${PGBIN:-$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)}"
if [[ -z "${PGBIN}" || ! -x "${PGBIN}/postgres" ]]; then
  echo "Postgres binaries not found; set PGBIN. Skipping." >&2
  exit 0
fi

WORK="$(mktemp -d)"
PORT="${PGPORT_TEST:-54339}"
RUN=()
if [[ "$(id -u)" == "0" ]]; then
  chown postgres "$WORK"
  RUN=(runuser -u postgres --)
fi

cleanup() {
  "${RUN[@]}" "$PGBIN/pg_ctl" -D "$WORK/data" -m immediate stop >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

"${RUN[@]}" "$PGBIN/initdb" -D "$WORK/data" -U postgres --auth=trust >/dev/null
"${RUN[@]}" "$PGBIN/pg_ctl" -D "$WORK/data" -o "-p $PORT -k $WORK -c listen_addresses=''" -l "$WORK/log" -w start >/dev/null

PSQL=("${RUN[@]}" "$PGBIN/psql" -h "$WORK" -p "$PORT" -U postgres -d postgres -v ON_ERROR_STOP=1 -q)

"${PSQL[@]}" -f "$ROOT/scripts/sql/supabase-shim.sql"
for f in "$ROOT"/supabase/migrations/*.sql; do
  echo "applying $(basename "$f")"
  "${PSQL[@]}" -f "$f"
done
"${PSQL[@]}" -f "$ROOT/scripts/sql/checks.sql"
echo "all database checks passed"

# The demo data script must load on a fresh database too.
"${RUN[@]}" "$PGBIN/createdb" -h "$WORK" -p "$PORT" -U postgres demo
DEMO=("${RUN[@]}" "$PGBIN/psql" -h "$WORK" -p "$PORT" -U postgres -d demo -v ON_ERROR_STOP=1 -q)
grep -v "^create role" "$ROOT/scripts/sql/supabase-shim.sql" | "${DEMO[@]}" 2>/dev/null
for f in "$ROOT"/supabase/migrations/*.sql; do "${DEMO[@]}" -f "$f"; done
"${DEMO[@]}" -f "$ROOT/scripts/sql/demo-seed.sql"
"${DEMO[@]}" -c "select (select count(*) from public.students) students, (select count(*) from public.invoices) bills, (select count(*) from public.attendance) attendance, (select count(*) from public.marks) marks"
