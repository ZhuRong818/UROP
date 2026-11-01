#!/bin/zsh
# Sequential driver for the SOTA baseline benchmark (user: "run them in sequence"). Resumes paused jobs one at a time.
cd /Users/zhurong/UROP
D=data/v7/sota_baselines_20261101; LOG=$D/sequence.log
say() { echo "$(date -u +%FT%TZ) $*" >> $LOG; }
waitpid() { while kill -0 $1 2>/dev/null; do sleep 30; done; }
say "start; waiting for Moirai-MoE (17654) and Tier C (24822)"
waitpid 17654; say "Moirai-MoE exited; files $(ls $D/tier_b/moirai_moe_*.parquet 2>/dev/null | wc -l)"
waitpid 24822; say "Tier C exited; files $(ls $D/tier_c/*.parquet 2>/dev/null | wc -l)"
kill -CONT 37362; say "resumed TabICL/CatBoost (37362)"; waitpid 37362
say "TabICL/CatBoost exited; tier_a files $(ls $D/tier_a/*.parquet | wc -l)"
kill -CONT 18412; say "resumed Sundial (18412)"; waitpid 18412
say "Sundial exited; files $(ls $D/tier_b/sundial_*.parquet 2>/dev/null | wc -l)"
.venv-ts/bin/python -m eventx.tasks.benchmark_v7_sota_baselines_20261101_v3 tier_b2 --models time_moe > $D/tier_b2_timemoe.log 2>&1
say "Time-MoE exited rc=$?; files $(ls $D/tier_b/time_moe_*.parquet 2>/dev/null | wc -l)"
say "SEQUENCE DONE"
