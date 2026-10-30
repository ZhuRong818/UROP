#!/bin/zsh
# Mechanical steps after scripts/close_out_20261030.sh finishes. Read-only for every evaluation: it never
# runs or reruns an evaluator. Waits for "close-out finished" in the close-out summary (max 24 h), then:
# 1. formats the three once-only results (report/fill_pending_20261030.py) into fill_pending.json;
# 2. runs the full reproducibility checker, then the --recompute variant;
# 3. writes a SHA-256 manifest of the close-out logs, result folders and every consumption receipt.
# Report text is NOT edited here. Usage: zsh scripts/post_close_out_20261030.sh
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python
OUT=data/close_out_20261030
LOG=$OUT/post_summary.log
for i in {1..1440}; do
  grep -q "close-out finished" $OUT/summary.log 2>/dev/null && ! pgrep -f "scripts/close_out_20261030.sh" >/dev/null && break
  sleep 60
done
mkdir -p $OUT
if ! grep -q "close-out finished" $OUT/summary.log 2>/dev/null; then
  echo "$(date -u +%FT%TZ) close-out not finished after 24 h; post steps NOT run" | tee -a $LOG; exit 1
fi
run() {  # run <name> <command...>
  local name=$1; shift
  echo "$(date -u +%FT%TZ) start $name" | tee -a $LOG
  nice -n 5 "$@" > $OUT/$name.log 2>&1
  echo "$(date -u +%FT%TZ) end $name rc=$?" | tee -a $LOG
}
run fill_pending $PY report/fill_pending_20261030.py
cp $OUT/fill_pending.log $OUT/fill_pending.json
run checker $PY -m eventx.tasks.verify_report_reproducibility_20261027
run checker_recompute $PY -m eventx.tasks.verify_report_reproducibility_20261027 --recompute
echo "$(date -u +%FT%TZ) start manifest" | tee -a $LOG
{
  for d in $OUT data/v7/forecast_runtime_20261026_v02b/evaluation data/v4/confirmatory data/v7/late_june_test_20261027_v2; do
    [ -d $d ] && find $d -type f ! -name 'backup_manifest.sha256' ! -name 'post_summary.log' -size -2000M
  done
  find data -name consumption_receipt.json
} | sort -u | while read f; do shasum -a 256 "$f"; done > $OUT/backup_manifest.sha256
echo "$(date -u +%FT%TZ) end manifest files=$(wc -l < $OUT/backup_manifest.sha256)" | tee -a $LOG
echo "$(date -u +%FT%TZ) post close-out finished" | tee -a $LOG
