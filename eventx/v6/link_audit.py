"""Association review validation; retrieval scores never become gold labels."""

def validate_reviews(packet, responses_a, responses_b):
    expected = {r["pair_id"]: r for r in packet}
    if not expected or len(expected) != len(packet):
        raise ValueError("Nonempty unique review packet required")
    indexes = []
    for responses in (responses_a, responses_b):
        index = {r["pair_id"]: r for r in responses}
        if len(index) != len(responses) or set(index) != set(expected):
            raise ValueError("Review IDs missing, extra or duplicated")
        reviewers = {r.get("reviewer_id") for r in responses}
        if len(reviewers) != 1 or not next(iter(reviewers)):
            raise ValueError("One real reviewer identifier required per submission")
        for identity, r in index.items():
            label = r["labels"]
            if label.get("relevance") not in {"direct", "background", "unrelated", "abstain"}:
                raise ValueError("Missing/invalid relevance label")
            if label.get("outcome_applicability") not in {
                "yes_proposition", "event_only", "not_applicable", "uncertain"}:
                raise ValueError("Missing/invalid outcome applicability")
            if not label.get("evidence_spans"):
                raise ValueError("Evidence required")
            article = expected[identity]["article"]
            source = "\n".join(article.get(k) or "" for k in ("headline", "summary"))
            for span in label["evidence_spans"]:
                if not isinstance(span, str) or not span.strip() or span not in source:
                    raise ValueError("Evidence must quote the supplied article")
        indexes.append(index)
    if responses_a[0]["reviewer_id"] == responses_b[0]["reviewer_id"]:
        raise ValueError("Distinct reviewers required; independence still needs attestation")
    disagreements = [k for k in expected if any(indexes[0][k]["labels"][f] !=
        indexes[1][k]["labels"][f] for f in ("relevance", "outcome_applicability"))]
    return {"pairs": len(expected), "disagreement_ids": disagreements,
            "adjudication_required": bool(disagreements), "human_independence_verified": False}
