#!/usr/bin/env zsh
set -euo pipefail

cd /Users/zhurong/UROP
nohup ./scripts/run_v3_historical_feasibility.sh \
  > data/v3_historical/feasibility/continuous_supervisor.log \
  2>&1 \
  < /dev/null &
disown
