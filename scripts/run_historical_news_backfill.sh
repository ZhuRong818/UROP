#!/usr/bin/env zsh
set -u

cd /Users/zhurong/UROP
output_root="data/exploratory/lumid_historical_news"
log_dir="data/exploratory/lumid_historical_news"
mkdir -p "$log_dir"

# Bounded, label-blind monthly exports. January and February 2025 already exist;
# continue through the last completed month currently available in Lumid.
months=(
  2025-03 2025-04 2025-05 2025-06 2025-07 2025-08 2025-09 2025-10 2025-11 2025-12
  2026-01 2026-02 2026-03 2026-04 2026-05 2026-06 2026-07
)

for month in $months; do
  start="${month}-01T00:00:00Z"
  next_month=$(date -j -v+1m -f "%Y-%m-%d" "${month}-01" "+%Y-%m-%d")
  end="${next_month}T00:00:00Z"
  target="$output_root/${month//-/}01T000000Z_${next_month//-/}01T000000Z/manifest.json"
  if [[ -f "$target" ]]; then
    print "SKIP $month (manifest exists)"
    continue
  fi
  print "START $month $start $end"
  .venv/bin/python -m eventx.tasks.export_v2_3_news_warehouse \
    --start "$start" --end "$end" --output-root "$output_root" --timeout 600
  status=$?
  print "END $month status=$status"
  if [[ $status -ne 0 ]]; then
    print "STOP after failure in $month"
    exit $status
  fi
done

print "HISTORICAL BACKFILL COMPLETE"
