#!/bin/zsh
# One-shot close-out after the live and V4 windows. Each underlying task refuses to rerun; this script
# refuses to start early and stops the V4 chain at its first failed gate (the frozen V4 rule).
# Order: V02b live evaluation -> V4 audit/consume/prepare/build/evaluate -> late-June capture/evaluate.
# V02 (partial, outage-terminated) is not evaluated: its source never wrote a capture manifest, which the
# frozen V02 evaluator requires. Usage: zsh scripts/close_out_20261030.sh
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python
OUT=data/close_out_20261030
if [ $(date -u +%s) -lt $(date -j -u -f %Y-%m-%dT%H:%M:%S 2026-10-30T00:00:30 +%s) ]; then
  echo "too early: windows close 2026-10-30T00:00Z"; exit 1
fi
mkdir -p $OUT
step() {  # step <name> <module> [args...]; returns the task's exit code
  local name=$1; shift
  echo "$(date -u +%FT%TZ) start $name" | tee -a $OUT/summary.log
  nice -n 5 $PY -m "$@" > $OUT/$name.log 2>&1
  local rc=$?
  echo "$(date -u +%FT%TZ) end $name rc=$rc" | tee -a $OUT/summary.log
  return $rc
}

# 1. Live V02b (sealed until 23:57:30Z on 29 Oct; the emitter stops itself after open_after).
while pgrep -f "eventx.tasks.(run|collect)_v7_forecast_runtime_20261026_v02b" >/dev/null; do sleep 30; done
step v02b_evaluate eventx.tasks.evaluate_v7_forecast_runtime_20261026_v02b

# 2. V4: wait for the collector to seal Oct 29 and exit, then the frozen chain, stopping at a failed gate.
STATE=data/v4/confirmatory/sealed_inputs/collector_state.json
for i in {1..360}; do
  grep -q sealed_collection_complete_pending_data_gate $STATE && ! pgrep -f collect_v4_confirmatory_warehouse >/dev/null && break
  sleep 60
done
if grep -q sealed_collection_complete_pending_data_gate $STATE && ! pgrep -f collect_v4_confirmatory_warehouse >/dev/null; then
  step v4_audit eventx.tasks.audit_v4_confirmatory_collection &&
  step v4_consume eventx.tasks.consume_v4_confirmatory_holdout &&
  step v4_prepare eventx.tasks.prepare_v4_confirmatory_inputs &&
  step v4_build eventx.tasks.build_v4_confirmatory_examples &&
  step v4_evaluate eventx.tasks.evaluate_v4_confirmatory
else
  echo "$(date -u +%FT%TZ) V4 collector not sealed/exited after 6 h; V4 chain NOT started" | tee -a $OUT/summary.log
fi

# 3. Late-June test: capture once, evaluate once only if capture succeeded.
step late_june_capture eventx.tasks.run_v7_late_june_test_20261027_v2 capture &&
step late_june_evaluate eventx.tasks.run_v7_late_june_test_20261027_v2 evaluate
echo "$(date -u +%FT%TZ) close-out finished" | tee -a $OUT/summary.log
