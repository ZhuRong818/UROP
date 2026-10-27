"""Snapshot bounded relevance submissions; never extract over frozen templates."""
import hashlib
import json
import stat
import zipfile
from pathlib import Path

from eventx.v6.link_audit import validate_reviews


def main():
    base = Path('data/v6')
    archive = base / 'bounded_submission_validation_20260917/relevance_AB_responses_completed.zip'
    packet_path = base / 'bounded_audit_20260917/relevance_review_packet.jsonl'
    out = base / 'bounded_relevance_receipt_20260917'
    names = [f'relevance_reviewer_{r}_responses.jsonl' for r in ('A', 'B')]
    sha = lambda b: hashlib.sha256(b).hexdigest()
    parse = lambda b: [json.loads(line) for line in b.decode('utf-8').splitlines() if line.strip()]
    with zipfile.ZipFile(archive) as z:
        assert sorted(z.namelist()) == sorted(names), 'Unexpected archive members'
        for item in z.infolist():
            assert item.file_size <= 10_000_000, 'Oversized member'
            assert not stat.S_ISLNK(item.external_attr >> 16), 'Symlink member'
        payloads = [z.read(name) for name in names]
    packet = parse(packet_path.read_bytes())
    reviews = [parse(b) for b in payloads]
    report = validate_reviews(packet, *reviews)
    indexes = [{r['pair_id']: r for r in rows} for rows in reviews]
    cases = {r['pair_id']: r for r in packet}
    adjudication = []
    for identity in report['disagreement_ids']:
        adjudication.append({'pair_id': identity, 'evidence': cases[identity],
            'review_A': indexes[0][identity], 'review_B': indexes[1][identity],
            'adjudicator': None, 'labels': None, 'rationale': None,
            'adjudication_attempts_used': 0, 'max_attempts': 1})
    report.update({'status': 'awaiting_single_round_adjudication',
        'agreed_cases': len(packet) - len(adjudication),
        'final_audit_evaluated': False, 'protected_outcomes_accessed': False,
        'archive_sha256': sha(archive.read_bytes()),
        'packet_sha256': sha(packet_path.read_bytes()),
        'scope': 'Fixed 40-case development relevance sample; no resampling.'})
    out.mkdir(exist_ok=False)
    for name, payload in zip(names, payloads):
        (out / name).write_bytes(payload)
    (out / 'adjudication_packet.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in adjudication))
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    manifest = {'inputs': {str(archive): sha(archive.read_bytes()), str(packet_path): sha(packet_path.read_bytes()),
        str(Path(__file__)): sha(Path(__file__).read_bytes())},
        'outputs': {p.name: sha(p.read_bytes()) for p in sorted(out.iterdir())}}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
