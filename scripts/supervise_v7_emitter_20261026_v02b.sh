#!/bin/zsh
# Restart the V02b emitter if it exits before the window closes (the emitter resumes its journal;
# elapsed grids are recorded as missed). Never restarts the source collector.
cd "$(dirname "$0")/.." || exit 1
LOG=data/v7/forecast_runtime_20261026_v02b/prospective/supervisor.log
END=$(.venv/bin/python -c "import json;print(int(json.load(open('data/v7/forecast_runtime_20261026_v02b/activation_receipt.json'))['open_after'])+60)")
while [ $(date +%s) -lt $END ]; do
  if ! pgrep -f "eventx.tasks.run_v7_forecast_runtime_20261026_v02b" >/dev/null; then
    echo "$(date -u +%FT%TZ) starting emitter" >> $LOG
    .venv/bin/python -m eventx.tasks.run_v7_forecast_runtime_20261026_v02b >> data/v7/forecast_runtime_20261026_v02b/prospective/emitter_stdout.log 2>&1 &
  fi
  sleep 60
done
echo "$(date -u +%FT%TZ) supervisor done" >> $LOG
