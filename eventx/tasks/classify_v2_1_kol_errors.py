"""Apply the counted, development-only taxonomy to the 37 KOL-v1 errors."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "v1_audit"
INPUT = ROOT / "kol_error_analysis_rows.jsonl"
OUTPUT = ROOT / "kol_error_taxonomy_rows.jsonl"
REPORT = ROOT / "kol_error_taxonomy.json"


MODE_DEFINITIONS = {
    "fp_generic_polysemous_overlap": {
        "error_type": "false_positive",
        "description": "Broad or polysemous tokens such as house, state, control, or democratic satisfy a proposition without referring to that proposition.",
        "recommended_change": "Separate strong subject anchors from geography/party/common nouns and require a proposition-specific signal bundle in one local segment; never let head/state/house/control alone act as an event match.",
    },
    "fp_wrong_event_or_person": {
        "error_type": "false_positive",
        "description": "The tweet concerns a different candidate, jurisdiction, race, or governmental event while sharing election vocabulary.",
        "recommended_change": "For candidate markets require the named candidate's full name or unambiguous surname plus an election-prospect signal; require jurisdiction agreement and disallow common given names as independent anchors.",
    },
    "fp_cross_segment_multitopic": {
        "error_type": "false_positive",
        "description": "A roundup or multi-topic tweet supplies the subject anchor in one item and the event word in another.",
        "recommended_change": "Split on sentences, line breaks, and bullets and require anchor/context co-occurrence inside the same segment, with only tightly adjacent segments eligible for combination.",
    },
    "fp_non_evidentiary_prediction_market": {
        "error_type": "false_positive",
        "description": "Prediction-market boilerplate repeats the proposition but reports only failed order/account mechanics.",
        "recommended_change": "Reject failed/rejected/cancelled/insufficient-balance order messages; accept market text only when it contains a realized trade, position, price, odds, or probability signal.",
    },
    "fp_entity_mention_without_outcome_evidence": {
        "error_type": "false_positive",
        "description": "The exact candidate and office are mentioned, but the content is personal or ceremonial and does not update electoral prospects.",
        "recommended_change": "Require a campaign, nomination, polling, endorsement, opposition, funding, scandal, withdrawal, or other prospect-bearing predicate in addition to the candidate identity.",
    },
    "fp_composite_annotation_inconsistency": {
        "error_type": "false_positive",
        "description": "One Senate-control row is labeled not relevant to a House-AND-Senate market, while six comparable Senate-only rows are labeled relevant; this conflicts with the audit rule that any reasonable probability update is relevant.",
        "recommended_change": "Freeze the original label unchanged but define component evidence as relevant to a conjunction when it can update the joint probability; require party, chamber, and prospect signals locally and treat the isolated conflict as development-label noise.",
    },
    "fn_multilingual_event_vocabulary": {
        "error_type": "false_negative",
        "description": "Portuguese election, polling, round, convention, and candidacy language is not present in the English event lexicon.",
        "recommended_change": "Add a frozen Portuguese election lexicon and diacritic-insensitive normalization while retaining the original exact text for audit evidence.",
    },
    "fn_indirect_geopolitical_capacity": {
        "error_type": "false_negative",
        "description": "Military capacity, escalation, sanctions, mobilization, strikes, weapons, or alliance support indirectly but genuinely updates an invasion/advance proposition.",
        "recommended_change": "For invasion/territorial propositions accept a named belligerent plus a frozen operational-capacity or escalation signal in the same segment; keep the rule proposition-specific rather than applying it to all categories.",
    },
    "fn_officeholder_status_synonym": {
        "error_type": "false_negative",
        "description": "An exact officeholder is paired with a status-changing phrase such as removed from power or gone, but not the literal market words head/leader/state.",
        "recommended_change": "Add officeholder status families (removed, ousted, deposed, resigned, dead, gone, successor, remains/in power) and require exact person identity.",
    },
    "fn_sports_performance_evidence": {
        "error_type": "false_negative",
        "description": "Player statistics or major-tournament progress updates award prospects without naming the award.",
        "recommended_change": "For individual award markets accept exact athlete identity plus frozen performance/availability/major-tournament signals such as goals, assists, injury, score, final, or World Cup stage.",
    },
    "fn_candidate_campaign_evidence": {
        "error_type": "false_negative",
        "description": "Attack advertising against the exact candidate is prospect-bearing campaign evidence but does not repeat nominee/governor.",
        "recommended_change": "Accept exact candidate identity plus campaign-action predicates including attack ad, endorsement, spending, fundraising, debate, withdrawal, and ballot access.",
    },
    "fn_candidate_scandal_evidence": {
        "error_type": "false_negative",
        "description": "A candidate-linked staff scandal is indirect reputation/prospect evidence even without election terms.",
        "recommended_change": "Accept exact candidate identity plus a bounded scandal/legal/investigation predicate; do not generalize this to unrelated associates lacking a direct candidate link.",
    },
    "fn_substantive_prediction_market_signal": {
        "error_type": "false_negative",
        "description": "A realized large wager with payoff information is treated as relevant probability evidence, but inflection mismatch prevents a match.",
        "recommended_change": "Normalize proposition verb families and allow realized wager/odds/price/position signals while retaining the failed-order exclusion.",
    },
}


ASSIGNMENTS: dict[str, tuple[str, str]] = {
    # False positives.
    "23c0d3d40ecac489": ("fp_wrong_event_or_person", "Michigan governor and House-primary discussion is not the national 2026 House-control event."),
    "29b79d6d60f052ad": ("fp_generic_polysemous_overlap", "Democratic/control occur in a Belarus repression discussion, not U.S. congressional control."),
    "2bc7cf1d4ba774c2": ("fp_wrong_event_or_person", "The Brazil election is mentioned, but Flávio Bolsonaro is absent and the item is about Lula's response."),
    "31dce416128b995d": ("fp_wrong_event_or_person", "The item concerns Flávio Bolsonaro and does not identify Lula or update Lula directly under the audit rubric."),
    "34b3fa063344ecd0": ("fp_non_evidentiary_prediction_market", "The proposition is copied into an insufficient-balance/failed-order notice with no realized signal."),
    "3f50049b994fa684": ("fp_cross_segment_multitopic", "Russia/Ukraine and peace are drawn from different items in a long overnight-news roundup."),
    "467ba299d0b09a7f": ("fp_cross_segment_multitopic", "Iran talks and the generic phrase state of politics occur in different topics; Mojtaba is absent."),
    "4d18b68a9a3597dc": ("fp_generic_polysemous_overlap", "Iran War plus Deep State creates a false Iran/state conjunction without Mojtaba or officeholder status."),
    "60611be07ecb6d59": ("fp_generic_polysemous_overlap", "House Republicans refers to a legislative vote, not the House-control election proposition."),
    "798544d2d335bbd5": ("fp_wrong_event_or_person", "James is John James and the jurisdiction is Michigan, not James Fishback in Florida."),
    "84dd5ec808d58554": ("fp_generic_polysemous_overlap", "A duplicate war-powers story uses House and Republicans only in legislative senses."),
    "b2b0699dda146afc": ("fp_wrong_event_or_person", "The campaign setback concerns Flávio Bolsonaro; Lula is not named in the item."),
    "dd2e6e5d1d0adaab": ("fp_cross_segment_multitopic", "Iran and head are supplied by separate bullets in a ten-item roundup; Mojtaba is absent."),
    "f3ee757de2d83cef": ("fp_entity_mention_without_outcome_evidence", "The exact candidate is mentioned only in a childbirth congratulations item."),
    "fc3b90b185ff6196": ("fp_composite_annotation_inconsistency", "The frozen label rejects a Senate-control update even though six comparable Senate-only audit rows are labeled relevant to the same conjunction."),
    # False negatives.
    "0698b7fdbe51f8c7": ("fn_sports_performance_evidence", "Harry Kane's goals and assists are direct performance evidence for an individual award."),
    "134426cd912f8051": ("fn_officeholder_status_synonym", "The exact person is explicitly described as removed from power."),
    "1ca4f0ffaa4f4f6f": ("fn_officeholder_status_synonym", "The exact person is paired with a quantified gone/status claim."),
    "2c9971c8b9db0a13": ("fn_multilingual_event_vocabulary", "Portuguese runoff polling gives a direct Lula-versus-Flávio margin."),
    "3a7e991830dae504": ("fn_indirect_geopolitical_capacity", "Mobilization and casualty information updates Russia's capacity to advance."),
    "492ce606d2d7b2b9": ("fn_candidate_scandal_evidence", "A scandal involving Lula's trusted former chief of staff is candidate-linked reputation evidence."),
    "50681a076125fe51": ("fn_substantive_prediction_market_signal", "The tweet reports a realized $87K bet and payoff, not failed account mechanics."),
    "5ddcfe0531a94e4c": ("fn_candidate_campaign_evidence", "A $400K attack-ad buy targets the exact gubernatorial candidate."),
    "688f19b4752bd878": ("fn_candidate_campaign_evidence", "An anti-Fishback Florida campaign ad is prospect-bearing evidence."),
    "73913d4364c9b336": ("fn_multilingual_event_vocabulary", "Portuguese first-round polling reports Lula's and Flávio's shares."),
    "7492e02a8ee28e1e": ("fn_indirect_geopolitical_capacity", "A revenge pledge by Iran's leader is escalation evidence for U.S.-Iran conflict risk."),
    "7fe7b74bce44b06c": ("fn_multilingual_event_vocabulary", "Portuguese text reports a rival's official presidential candidacy and attacks on Lula."),
    "81aa4c19062cf7a3": ("fn_multilingual_event_vocabulary", "Portuguese runoff polling reports a technical tie involving Lula."),
    "81c0bd22a7404cbe": ("fn_indirect_geopolitical_capacity", "Russian strikes and blockade activity are operational evidence under the review rubric."),
    "8c01b3068faa2e54": ("fn_multilingual_event_vocabulary", "Portuguese convention coverage is tied to Flávio Bolsonaro's candidacy."),
    "9df5b75eec8800ee": ("fn_indirect_geopolitical_capacity", "Potential North Korean troops update Russia's military capacity."),
    "a8332bbac683623a": ("fn_multilingual_event_vocabulary", "Portuguese runoff polling gives Flávio's direct vote share."),
    "d072eb2f63dff21f": ("fn_multilingual_event_vocabulary", "Portuguese first-round polling gives Flávio's direct vote share."),
    "de8309eb5541c83f": ("fn_indirect_geopolitical_capacity", "New sanctions are pressure on Russia's capacity under the review rubric."),
    "e6c7862229713d5c": ("fn_indirect_geopolitical_capacity", "Russian intelligence assistance is treated as capacity/alliance evidence under the review rubric."),
    "fbb5dfbe8423d1fe": ("fn_indirect_geopolitical_capacity", "New ballistic-missile launchers update Russia's military capacity."),
    "fd272d8189abd656": ("fn_sports_performance_evidence", "Harry Kane's World Cup knockout-stage prospects bear on his award candidacy."),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def atomic_write(path: Path, payload: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload)
    temporary.replace(path)


def main() -> None:
    rows = read_jsonl(INPUT)
    indexed = {row["audit_id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise SystemExit("duplicate audit IDs in extracted errors")
    if set(indexed) != set(ASSIGNMENTS):
        missing = sorted(set(indexed) - set(ASSIGNMENTS))
        extra = sorted(set(ASSIGNMENTS) - set(indexed))
        raise SystemExit(f"taxonomy assignment mismatch; missing={missing}, extra={extra}")

    enriched = []
    for audit_id in sorted(indexed):
        mode, diagnosis = ASSIGNMENTS[audit_id]
        row = indexed[audit_id]
        definition = MODE_DEFINITIONS[mode]
        if definition["error_type"] != row["error_type"]:
            raise SystemExit(f"{audit_id}: mode/error-type mismatch")
        enriched.append(
            {
                **row,
                "failure_diagnosis": diagnosis,
                "primary_failure_mode": mode,
                "recommended_change": definition["recommended_change"],
            }
        )
    atomic_write(OUTPUT, "".join(json.dumps(row, sort_keys=True) + "\n" for row in enriched))

    counts = Counter(row["primary_failure_mode"] for row in enriched)
    by_error = Counter(row["error_type"] for row in enriched)
    report = {
        "association_rule": "eventx-v2.1-association-rule-v1-candidate",
        "development_only": True,
        "error_counts": dict(sorted(by_error.items())),
        "input": {"path": relative(INPUT), "sha256": sha256_file(INPUT)},
        "mode_counts": dict(sorted(counts.items())),
        "modes": {
            mode: {**definition, "count": counts[mode]}
            for mode, definition in sorted(MODE_DEFINITIONS.items())
        },
        "output": {"path": relative(OUTPUT), "rows": len(enriched), "sha256": sha256_file(OUTPUT)},
        "status": "taxonomy_complete",
    }
    atomic_write(REPORT, json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
