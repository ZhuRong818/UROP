"""Audit a V4 collector restart using process, checkpoint, and receipt metadata only."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SEALED = ROOT / 'data/v4/confirmatory/sealed_inputs'
PROTOCOL_ID = 'eventx-v4-confirmatory-polymarket-20260902'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def process_rows(pids: list[int]) -> list[dict]:
    command = ['ps', '-o', 'pid=,ppid=,stat=,etime=,comm=', '-p', ','.join(map(str, pids))]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError(f'ps failed with exit {result.returncode}')
    rows = []
    for line in result.stdout.splitlines():
        pid, ppid, status, elapsed, executable = line.split(None, 4)
        rows.append({'pid': int(pid), 'ppid': int(ppid), 'status': status,
                     'elapsed': elapsed, 'executable': executable})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restart-receipt', type=Path, required=True)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    receipt_path = args.restart_receipt.resolve()
    if not receipt_path.is_relative_to(SEALED.resolve() / 'restart_receipts'):
        raise SystemExit('restart receipt must be in sealed_inputs/restart_receipts')
    restart = json.loads(receipt_path.read_text())
    state_path = SEALED / 'collector_state.json'
    state = json.loads(state_path.read_text())
    lock = json.loads((SEALED / 'collector.lock').read_text())
    launch = json.loads((SEALED / 'launch_receipt.json').read_text())
    collection = json.loads((ROOT / 'eventx/release/v4/collection_manifest.json').read_text())
    manifest = json.loads((ROOT / 'eventx/release/v4/holdout_implementation_manifest.json').read_text())

    collector_pid = int(restart['collector_pid'])
    guard_pid = int(restart['guard_pid'])
    processes = process_rows([collector_pid, guard_pid])
    present = {row['pid'] for row in processes if not row['status'].startswith('Z')}
    problems = []
    if collector_pid not in present:
        problems.append('collector not running')
    if guard_pid not in present:
        problems.append('caffeinate guard not running')
    if int(lock['pid']) != collector_pid:
        problems.append('restart receipt and active lock PID differ')
    if state['protocol_id'] != PROTOCOL_ID or restart['protocol_id'] != PROTOCOL_ID:
        problems.append('protocol ID mismatch')
    if state['labels_predictions_or_metrics_computed'] is not False:
        problems.append('state indicates protected computation')

    collector_path = ROOT / collection['collector']['path']
    collector_hash = sha256(collector_path)
    if not (collector_hash == collection['collector']['sha256']
            == launch['collector_code_sha256']
            == restart['collector_code_sha256']):
        problems.append('collector code hash mismatch')
    cohort_hash = sha256(ROOT / 'data/v4/confirmatory/cohort_gate/cohort.jsonl')
    protocol_hash = sha256(ROOT / 'eventx/release/v4/protocol.json')
    if cohort_hash != collection['cohort_sha256']:
        problems.append('cohort hash mismatch')
    if protocol_hash != collection['protocol_sha256']:
        problems.append('protocol hash mismatch')
    frozen = [{'path': item['path'],
               'matches': sha256(ROOT / item['path']) == item['sha256']}
              for item in manifest['artifacts']]
    if not all(item['matches'] for item in frozen):
        problems.append('frozen implementation hash mismatch')

    archived_lock = ROOT / restart['archived_stale_lock']
    if not archived_lock.is_file():
        problems.append('archived stale lock missing')
    elif int(json.loads(archived_lock.read_text())['pid']) != int(restart['previous_collector_pid']):
        problems.append('archived stale lock PID mismatch')

    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    stop = min(today, datetime(2026, 10, 30, tzinfo=timezone.utc))
    partition_checks = {}
    for kind, start, names, key in (
        ('news', datetime(2026, 8, 30, tzinfo=timezone.utc), ['articles'], 'next_news_day'),
        ('trades', datetime(2026, 9, 6, tzinfo=timezone.utc),
         [f'batch_{i:03d}' for i in range(1, 11)], 'next_trade_day'),
    ):
        completed = parse_time(state[key])
        days = (completed - start).days
        complete = 0
        for offset in range(days):
            day = (start + timedelta(days=offset)).date().isoformat()
            for name in names:
                base = SEALED / kind / day
                files = [base / f'{name}{suffix}' for suffix in ('.jsonl', '.sql', '_receipt.json')]
                if not all(path.is_file() for path in files):
                    problems.append(f'missing batch file: {kind}/{day}/{name}')
                    continue
                receipt = json.loads(files[2].read_text())
                if not (len(receipt.get('data_sha256', '')) == 64
                        and len(receipt.get('sql_sha256', '')) == 64
                        and receipt.get('receipt', {}).get('run_id')):
                    problems.append(f'malformed receipt: {kind}/{day}/{name}')
                    continue
                complete += 1
        state_days = state['completed_news_days' if kind == 'news' else 'completed_trade_days']
        if state_days != days:
            problems.append(f'{kind} checkpoint count mismatch')
        partition_checks[kind] = {'checkpointed_days': days,
                                  'receipts_present_with_payload_and_sql_files': complete,
                                  'closed_days_pending': max(0, (stop - completed).days)}

    protected = {rel: (SEALED.parent / rel).exists() for rel in (
        'consumption_receipt.json', 'examples/examples.bin', 'evaluation/result.json',
        'evaluation/predictions.bin', 'evaluation/evaluation_attempt_receipt.json')}
    if any(protected.values()):
        problems.append('protected downstream artifact unexpectedly exists')

    report = {
        'checked_at': now.isoformat(),
        'scope': 'process_checkpoint_receipt_metadata_and_frozen_hashes_only',
        'restart_receipt': str(receipt_path.relative_to(ROOT)),
        'restart_receipt_sha256': sha256(receipt_path),
        'state': state,
        'state_sha256': sha256(state_path),
        'processes': processes,
        'collector_alive': collector_pid in present,
        'guard_alive': guard_pid in present,
        'restart_pid_matches_lock': int(lock['pid']) == collector_pid,
        'original_launch_pid': int(launch['pid']),
        'collector_code_matches_original_and_restart': collector_hash == collection['collector']['sha256'] == launch['collector_code_sha256'] == restart['collector_code_sha256'],
        'partition_checks': partition_checks,
        'frozen_hash_checks': frozen,
        'protected_artifact_existence_only': protected,
        'problems': problems,
        'sealed_payloads_or_outcomes_opened': False,
        'source_completeness_or_payload_integrity_certified': False,
    }
    out = ROOT / 'data/v4/health_checks' / now.strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    target = out / 'report.json'
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({
        'report': str(target.relative_to(ROOT)),
        'collector_alive': report['collector_alive'],
        'guard_alive': report['guard_alive'],
        'restart_pid_matches_lock': report['restart_pid_matches_lock'],
        'collector_code_matches_original_and_restart': report['collector_code_matches_original_and_restart'],
        'frozen_hashes_matching': sum(item['matches'] for item in frozen),
        'partition_checks': partition_checks,
        'protected_artifact_existence_only': protected,
        'problems': problems,
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
