#!/bin/zsh
set -euo pipefail

cd /Users/zhurong/UROP
source .venv/bin/activate
python -m eventx.tasks.fetch_v3_historical_development_trades
