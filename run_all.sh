#!/usr/bin/env bash
# Rebuild the whole implementation from an empty ERPNext, in go-live order.
#   ./run_all.sh            reuse the running sandbox if it is fresh
#   ./run_all.sh --fresh    destroy the sandbox (all ERPNext data) and start clean
set -euo pipefail
cd "$(dirname "$0")"
unset PYTHONPATH                      # keep host Python paths (e.g. ROS) out of the venv
PY=.venv/bin/python
DC="docker compose -f infra/docker-compose.yml -p skyforge"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

if [[ "${1:-}" == "--fresh" ]]; then
  step "Resetting ERPNext sandbox"
  $DC down -v
fi

step "Starting ERPNext"
$DC up -d
until [[ "$($DC ps -a --format '{{.State}}' create-site 2>/dev/null)" == "exited" ]]; do sleep 5; done
until curl -sf http://localhost:8080/api/method/ping >/dev/null; do sleep 3; done

step "Phase 2: configuration"
$PY -m config.configure

step "Phase 4: data migration"
$PY tools/generate_legacy_data.py
$PY -m migration.run --dry-run --no-decisions | grep cleansed     # first-pass view: what needed decisions
$PY -m migration.run
$DC exec -T backend bench --site frontend backup | grep -E "Database|successfully"   # pre-go-live restore point

step "Phase 3: first month of operations"
$PY -u -m scenarios.business_cycle
$DC exec -T backend bench --site frontend execute erpnext.stock.reorder_item.reorder_item >/dev/null
echo "  reorder job executed"
$PY -m scenarios.report

step "Phase 5a: supplier SOAP price sync"
$PY -m integration.supplier_soap_service & SOAP_PID=$!
sleep 2
$PY -m integration.price_sync
kill $SOAP_PID

step "Phase 5b: website order intake API"
.venv/bin/uvicorn integration.order_intake_api:app --port 8090 --log-level warning & API_PID=$!
until curl -sf http://127.0.0.1:8090/health >/dev/null; do sleep 1; done
$PY -m tools.sample_web_order
kill $API_PID

step "Tests (unit + live UAT)"
$PY -m pytest -q
