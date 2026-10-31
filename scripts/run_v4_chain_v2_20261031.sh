#!/bin/zsh
# One-shot V4 chain after the disclosed audit revision (eventx/release/v4/AUDIT_REVISION_V2_20261031.md).
# v2 audit -> frozen consume -> prepare -> build -> evaluate, each once, stopping at the first failure.
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python
OUT=data/v4_chain_20261031
[ -e $OUT/summary.log ] && { echo "already run"; exit 1; }
mkdir -p $OUT
step() {
  local name=$1; shift
  echo "$(date -u +%FT%TZ) start $name" | tee -a $OUT/summary.log
  nice -n 5 $PY -m "$@" > $OUT/$name.log 2>&1
  local rc=$?
  echo "$(date -u +%FT%TZ) end $name rc=$rc" | tee -a $OUT/summary.log
  return $rc
}
step v4_audit_v2 eventx.tasks.audit_v4_confirmatory_collection_v2_20261031 &&
step v4_consume eventx.tasks.consume_v4_confirmatory_holdout &&
step v4_prepare eventx.tasks.prepare_v4_confirmatory_inputs &&
step v4_build eventx.tasks.build_v4_confirmatory_examples &&
step v4_evaluate eventx.tasks.evaluate_v4_confirmatory
echo "$(date -u +%FT%TZ) chain finished" | tee -a $OUT/summary.log
