"""Commit the blind semantic review of the frozen pre-test KOL audit sample."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from eventx.settings import REPO_ROOT


MATCHED_RELEVANT = {
    # Karen Bass
    "4ad653bf1ca69950", "72f8e17018ff1883", "78e42c1fa636ad74",
    "7dbb187fdf124432", "7e233f51ca84501d", "84c6a22054cbc1dd",
    "8d40b188353c90cb", "b520b7de76d4b379", "d4982540ee221d56",
    "e364813ccb095be8",
    # Gavin Newsom
    "0e7f610be60f75b3", "21af28c877c55af0", "495c446978d1cc05",
    "5dd2bb8b6e5e3338", "74c234f58351021b", "a0bb64b9ed1f4c66",
    "bd38517921f58db3", "f9ab3c8e207fd843",
    # J.D. Vance nomination
    "1331e4aaa4f21140", "48722c8ccb2294a2", "87f38b8f23649d35",
    # Marco Rubio nomination
    "4bea5bc3f4be4298", "8378ae3d5d220e3c", "874550816e4d2b54",
    "97228be41cf2b1eb", "a6f2ad1f733912b6", "c35d7ae11e290c60",
    "d31a17d8bea45c28", "ee999d79c518bc1e", "fdac17746bd63bf6",
    # Mojtaba public appearance
    "4affbc745d4b68f8", "85e9bae1d5be74bb",
    # Mojtaba head of state
    "226858455a2007f8", "4074512b524d5b2c", "67ec5bc975e88036",
    "93188dd0fc6aae74", "a8f1d62acd10f3e2", "acfb8a02ec743356",
    "cc43d7c26ee6e471", "e03d8e5e7489e144", "f2422895d453fa1a",
    "f472c2489ac10fa9",
    # United Russia
    "1af8e689fe548942", "67cdb653d23dd0a6", "7b4acb108628e8cb",
    "9ee2d8ca5e3fd2ce",
    # Israel withdrawal from Lebanon
    "0517488d9dde1137", "11d36eb4a44cc876", "1f22a8f55dd25ea6",
    "27061c4c576b705a", "2db95cdc8d27beff", "3cbe92f6112991da",
    "474b7c6193e202e6", "5750761bbd4c8919", "68335dcb39edbda5",
    "945c2325424c7882", "94654b668ef87dba", "9d7db96ce4d4565a",
    "c29df8c0252a41e7", "cf930916dc01a073", "d5ed6bb6fe7bf618",
    "e7ed96dcddd24ef5", "f3e447c3cf83c70d",
    # Strait of Hormuz
    "0f3d87e925793694", "16154c16d58fa1d7", "168b26c23db39c94",
    "193976af9bbf210e", "19c332fefa07e5c1", "26907f6bd51f9f54",
    "2967860644900729", "2c56fe28c2d7795a", "3412dfd346c75bae",
    "3841d83fbb754c64", "3aff8abec6b020c4", "3b1a22af54b49cd6",
    "4399e745add07334", "4446e3f229833da0", "46972ee007dc9adb",
    "4fad5e3aca84248e", "5704e3b2cdfb6ba7", "57626573143e2d6f",
    "5f77629ecf809651", "680d3848106867cd", "692d82f93971d8a1",
    "77d3263138b867d9", "827fcb9cb3999827", "831ee4e24ed265e5",
    "84bfc76a7296670d", "87a14b5dfdfd6581", "8e2b84bd715eee46",
    "8e6698f0735419a5", "8fbace8a456f1044", "8fc534cded224010",
    "902716c8c29ea5c2", "957dacf43051f9d1", "9b59a3833d490352",
    "a64318df83f2acce", "a738aab46a945fab", "acea1d27c5095495",
    "b3a791051ef21c2e", "bf331f503c12d8cc", "c15a77418075f374",
    "cb5d7770edc60446", "cf47156636f43396", "d35d714254560012",
    "d827b054252cb15f", "ddc34f7a8c567fa4", "e64bf6a9fd7999dc",
    "efb125af90dd7371", "f066812c122a656b", "f0c53a0b8962fefc",
    "f1abf3d85237aec4", "f56a0dd786c3d036", "f7611acee493f4c6",
    "f81ca1fd42c37b83", "f8634114f95a3acf", "fa282416a74256de",
    # Cuba
    "607047773877fdac", "790c70f10994cd21", "8a471d9faf161fb8",
    "e15f75da2a78fc84",
    # Netanyahu / Bennett succession
    "e470ab4f11105807",
    "2286ae3e1207206f", "522d4ada1d3564aa", "d2cec6b276740733",
    # JD Vance presidency
    "3788010969193a00", "c576af3fa4f16cff", "cc75a622f7414bd4",
    "cc852d0b5cadeac2", "e52146638adf4f91", "fdcb94b589de74b2",
    # Hantavirus
    "3267953cf11c65f8", "772e13b2a85e5e43", "7be95f2af2f6dbff",
    "7fc0f056f2cbff4e", "c648c55e7acdd4ab",
    # China/Taiwan
    "3eb2c42465674e6a", "b04b6f3eb47c16be", "b10f12a74b2cad4f",
    "c14ae30424b2157a", "d7b9da9ebb7b547c", "e8e0f79fb629a081",
    "fad7bb5922a51fe7",
    # Lula election
    "7dfed0ec26961bdf", "b3bd8308d4ae9d41", "cceb7f5e29f38cca",
    "e4aefb235a84d1e6",
}

UNMATCHED_RELEVANT = {
    "86448b2313d0934d",  # Karen Bass vote count
    "fed9161d6bab8a15",  # United Russia Duma primaries
    "664fdea484f01188", "d13072f5f40ba872",  # Hormuz flows
    "b7149836be87ddba", "e68ea064fd46a07f",  # Andy Burnham succession
    "2f123b064e89c34c", "54141b77e20810fd", "5d54aa6f642af91c",
    "98df816121472fbc", "acea4778b2ba73ef",  # Xavier Becerra race
    "1706d99b05bb3f66", "7a941e300a44e21f",  # China/Taiwan invasion
}

RUBRIC = (
    "Relevant only when the tweet discusses the outcome, a named contender, "
    "or a concrete political, military, health, or market development that could "
    "reasonably update the contract probability. Mere shared names, titles, dates, "
    "countries, or generic topical proximity are not relevant."
)


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def main() -> None:
    audit_dir = REPO_ROOT / "data" / "v1" / "audit"
    sample_path = audit_dir / "kol_association_audit_sample.jsonl"
    rows = [json.loads(line) for line in sample_path.open() if line.strip()]
    ids = {row["audit_id"] for row in rows}
    unknown = (MATCHED_RELEVANT | UNMATCHED_RELEVANT) - ids
    if unknown:
        raise SystemExit(f"Review IDs are absent from the frozen sample: {sorted(unknown)}")

    for row in rows:
        relevant = (
            row["audit_id"] in MATCHED_RELEVANT
            if row["sample_type"] == "matched"
            else row["audit_id"] in UNMATCHED_RELEVANT
        )
        row["review_label"] = "relevant" if relevant else "not_relevant"
        row["review_rationale"] = (
            "Meets the event-update relevance rubric."
            if relevant
            else "Only generic, tangential, or wrong-event overlap under the audit rubric."
        )
        row["reviewer"] = "codex_semantic_review_v1"

    temporary = sample_path.with_suffix(".jsonl.tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    temporary.replace(sample_path)

    matched = [row for row in rows if row["sample_type"] == "matched"]
    unmatched = [row for row in rows if row["sample_type"] == "hard_unmatched"]
    matched_relevant = sum(row["review_label"] == "relevant" for row in matched)
    unmatched_relevant = sum(row["review_label"] == "relevant" for row in unmatched)

    by_reason: dict[str, Counter[str]] = defaultdict(Counter)
    by_market: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        label = row["review_label"]
        by_market[row["question"]][f"{row['sample_type']}:{label}"] += 1
        if row["sample_type"] == "matched":
            reason = "+".join(sorted(row.get("match_reason") or ["unknown"]))
            by_reason[reason][label] += 1

    report: dict[str, Any] = json.loads(
        (audit_dir / "kol_association_audit_report.json").read_text()
    )
    report.update(
        {
            "status": "reviewed",
            "reviewer": "codex_semantic_review_v1",
            "rubric": RUBRIC,
            "matched_reviewed": len(matched),
            "matched_relevant": matched_relevant,
            "stratified_sample_precision": ratio(matched_relevant, len(matched)),
            "hard_unmatched_reviewed": len(unmatched),
            "hard_unmatched_relevant": unmatched_relevant,
            "hard_candidate_false_negative_rate": ratio(
                unmatched_relevant, len(unmatched)
            ),
            "by_reason": {
                reason: {
                    **dict(counts),
                    "precision": ratio(counts["relevant"], sum(counts.values())),
                }
                for reason, counts in sorted(by_reason.items())
            },
            "by_market": {
                question: dict(counts) for question, counts in sorted(by_market.items())
            },
            "limitations": [
                "Precision is from a stratified audit sample, not a prevalence-weighted estimate.",
                "The false-negative rate applies to hard retrieval candidates, not all unmatched tweets.",
                "Review used train and validation timestamps only; test-period tweets were excluded.",
            ],
        }
    )
    (audit_dir / "kol_association_audit_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
