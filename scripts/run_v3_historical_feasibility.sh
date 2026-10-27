#!/usr/bin/env zsh
set -euo pipefail

cd /Users/zhurong/UROP
caffeinate -dimsu .venv/bin/python -m eventx.tasks.run_v3_historical_feasibility \
  --continuous \
  --retry-wait-seconds 900
