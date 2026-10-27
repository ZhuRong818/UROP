# V6 story/family boundary audit — certification withheld

## Decision

**The current 600-pair reservation cannot be certified yet.** Mechanical ID
separation passes, but known unresolved/unadopted cross-group relationships were
not incorporated into the reservation exclusion policy. This audit is outcome-blind;
no relevance labels, forecast prices, outcomes or performance were consulted.

Authoritative artifacts:

- `data/v6/boundary_audit_20260916/report.json`
- `data/v6/boundary_quarantine_20260916/report.json`

## What was checked

Verified prior release hashes. Compared200 development articles with100 reserved
articles for normalized exact headline/summary matches: **zero matches**. Searched
all20,000 cross-split article pairs with word/bigram and character TF-IDF; retained
the union of each reserved article's top3 per channel: **444 story review pairs**.
This complements, but does not certify, the previous neural similarity screen.

Inspected all member contracts of424 development and165 reserved provisional groups,
including members absent from the article-link packet. Word/character top3 search
produced **697 family-boundary review pairs**. Zero literal group-ID overlap remains
true, but is insufficient for semantic isolation.

Mapped all52 unresolved and6 proposed-but-unadopted historical links onto the
current complete event graph. Conservatively unioned these58 edges for a quarantine
preview, preserving unsampled intermediary nodes. This is not an adopted family
graph or a declaration that every uncertain edge is true.

## Concrete cross-split issues

| Boundary | Evidence inspected | Current disposition |
|---|---|---|
| CONFESSIONS II pure sales versus album-equivalent units | Same artist/album, US market, July3–9 tracking week and resolution schedule; distinct measurement definitions | Proposed link remains subject to independent review; quarantine across the split |
| xperiment pure sales versus album-equivalent units | Same artist/album, US market, July3–9 tracking week and resolution schedule | Same disposition |
| Top AI model June29 versus June30 | Recovered rules explicitly specify different days at10AM ET and the same style-control/tie-break procedure | Not identical snapshots; repeated-leaderboard dependency policy still needs resolution; conservative quarantine |

Rule evidence: `data/v5/provenance_recovery_20260908/reassessment_20260915_recovered_rule_text.jsonl`.
These records are retrospective semantic evidence, not historical feature admission.

The three reserved groups account for **194/600 pairs**. A hashed exclusion overlay
lists all194 pair IDs. The remaining preview has **406 pairs,162 groups,100 articles**.
It is **not certified**. The original600-pair packet and family graph are unchanged.
No automatic refill or post-exclusion population-precision claim is permitted;
sampling/weighting must be re-frozen after boundary decisions.

## Story inspection findings and limits

An assistant inspected the eight highest lexical-similarity candidates. Several
high scores came from boilerplate class-action or analyst-rating headlines about
different companies, rather than duplicate stories. Other examples shared a company
but described different dated reports. This is an assistant pre-audit, not independent
human review, and it does not establish separation of all stories.

Zero exact matches, low lexical similarity and cosine below0.8 cannot rule out
paraphrases, related updates or bridge articles. The screened population is only
these sampled articles, not all Lumid or public news. Semantic separation is not a
certificate of statistical independence under common calendar shocks.

## Review files and rules

1. `data/v6/boundary_audit_20260916/story_review_packet.jsonl` —444 cross-split pairs.
   Label `same_story`, `related_update`, `distinct_story`, or `unresolved`; cite article
   spans and identify underlying entity/event/date. The same topic or template alone
   is not the same story. A factual update of one story stays linked conservatively.
2. `data/v6/boundary_audit_20260916/family_review_packet.jsonl` —697 candidate pairs.
   Label `must_link`, `no_direct_link_established`, or `unresolved`; cite contract
   IDs, named outcomes, dates, rule text and structural dependence. Different dates
   alone do not establish a safe split. Read full member context, not just one title.
3. Review the58 known edges and specifically the three cross-split issues above;
   perform whole-boundary checks for missed aliases/stages beyond nearest-neighbour
   candidates. Top3 selection is not exhaustive certification.

Two real reviewers should fill separate copies, with reviewer identifiers and
rationales, before seeing each other's decisions. Do not share `score_ledger.jsonl`
or forecast outcomes. Adjudicate disagreements separately. Existing user-attested
human reviews remain valid historical evidence; this automated audit does not
replace them or invent new reviewers.

After decisions, publish a new group/story map and audit version, reject all retained
must-links crossing splits, quarantine unresolved boundaries, and re-freeze sampling.
Only then consider consuming independent association labels. Source availability,
model eligibility, recall coverage and statistical inference are separate gates.
