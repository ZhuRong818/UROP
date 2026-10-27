# Inspection of nine enriched-rule ranking changes

Date: 2026-09-21. Assistant development diagnostic, **not independent review,
gold labels, association certification, or predictive evaluation**.

## Evidence and method

Inspected all nine changed articles (headline/summary), old/new contract questions,
and recovered rules from `data/v6/enriched_rule_comparison_20260921/` against
`data/v6/expanded_coverage_20260919/articles.jsonl`. Output hashes from the comparison
manifest were verified. Reconstructed the shared-IDF unigram/bigram TF-IDF vectors
to inspect individual shared-term contributions; retained the original stored scores.
No frozen artifact, matcher, admission decision, or protected outcome was changed.

These are forced top rankings within retrieved candidates, not accepted links.
The retrospective vocabulary/cards are not a point-in-time deployment certificate.

## Findings

| Article ID / subject | Previous top → enriched top | Assessment and evidence |
| --- | --- | --- |
| 166357183 — IBIT in-kind redemptions | Bitcoin $85k in May → Bitcoin $1m before GTA VI | Genuine Bitcoin/ETF context, but no justification for this threshold/deadline switch. Enriched overlap includes `game` (0.01436 cosine contribution) from the headline's “Change the Game” and the contract's literal game release; this is a spurious sense match. `bitcoin` contributes 0.05332. |
| 168034724 — Strategy sells Bitcoin | Bitcoin $1m before GTA VI → Bitcoin $150k by June 30 | Plausible asset-level news, not evidence that the new contract is more relevant. `btc` (0.07640) and `bitcoin` (0.06617) explain all enriched similarity for the new top. Rules improve asset vocabulary coverage, not threshold/horizon attribution. |
| 185372398 — Alcoa Norway power agreements | Norway wins World Cup → Norway wins June 26 game | Incorrect country-to-football-team association. New-top overlap is only `norway` (0.09644) and `2026` (0.00240); article concerns an industrial site, not football. |
| 189385410 — Trump quantum-industry measures | Trump says Autism → Trump says Goat | Neither target utterance appears. Rules explicitly exclude official acts such as executive orders/bills signed; nevertheless `orders` contributes 0.01525 to similarity. Exclusion text becomes positive lexical evidence. Top switch itself is numerical noise (see below). |
| 189518836 — Schiff criticizes Saylor's Bitcoin bet | Bitcoin $1m before GTA VI → Bitcoin $150k by June 30 | Bitcoin commentary can be contextual news, but does not discriminate these contracts. New-top overlap is `btc`, `bitcoin`, and `trade`; the last contributes 0.04095 through price-source/trading rules rather than contract-specific evidence. |
| 197785133 — Axon stock and Trump's reported purchase | Trump says Autism → Trump says Goat | Mention of Trump is not a qualifying utterance. Shared terms are `trump` and `president`; neither target word is supported. Top switch is numerical noise. |
| 197899180 — Trump demands lower gas prices | Trump says Autism → Trump says Goat | A demand may be speech, but not evidence of either required word. Shared terms are `trump` and `market`, not the qualifying phrase. Top switch is numerical noise. |
| 201756152 — Strategy stock price target | Bitcoin $1m before GTA VI → Bitcoin $100k by December 31 | Bitcoin-related headline, but the reported $136/$260 analyst targets concern Strategy stock. New-top overlap is `price` (0.03378) and `bitcoin` (0.02420). Do not interpret a stock target as a Bitcoin threshold signal. |
| 211869183 — Google Search usage after Argentina win | Google best AI model → Argentina wins World Cup | One plausible topical repair: an actual Argentina World Cup match update is closer than a Google AI leaderboard contract. Shared Argentina/World Cup/win terms support that interpretation. The unspecified late match win does not establish tournament victory or a certified predictive link. |

### Three switches are effectively ties

For all three Trump cases, old and new question scores are exactly equal. Enriched
scores differ only at floating-point precision:

| Article | Enriched score: Autism | Enriched score: Goat | Difference |
| --- | --- | --- | --- |
| 189385410 | 0.041353974044357214 | 0.04135397404435723 | 1.3877787807814457e-17 |
| 197785133 | 0.02915987130962258 | 0.029159871309622585 | 3.469446951953614e-18 |
| 197899180 | 0.02207480740096143 | 0.022074807400961433 | 3.469446951953614e-18 |

Thus nine exact top-ID changes include three numerical near-tie switches, not nine
substantive changes in evidence. The existing exact-score sorting has no tolerance.

## Interpretation

- One plausible event-topic improvement (Argentina), still unvalidated.
- Four Bitcoin-context cases with unsupported contract-specific ranking gains.
- Four clearly inapplicable new matches: Norway industry-to-football and three
  Trump keyword contracts; the latter three are also numerical near-ties.
- Zero newly certified or admitted links. These judgments are not an accuracy estimate.

Rule concatenation is not a demonstrated semantic improvement. It adds useful asset
aliases, but also generic resolution language, exclusion clauses, ambiguous words,
and document-normalization effects. A relevant predictive article need not literally
mention a strike or settlement threshold: asset-level mechanism relevance and exact
contract attribution must be represented separately, rather than rejecting all
indirect news or forcing a particular threshold variant.

## Recommended next development change (not implemented here)

1. Report tolerance-aware top-score ties and abstain on unsupported specificity.
2. Bind typed entities (country/team, company/underlying asset) and target predicates.
3. Separate operative rules, exclusions, and resolution-source boilerplate; do not
   count exclusion-clause overlap as positive evidence of a qualifying event.
4. Retrieve asset/event-family news first, then assess contract horizon/variant
   applicability. Preserve contextual links as distinct from settlement evidence.
5. Compare this field-aware method on the same opened development set before any
   independent validation. Keep source/version/family gates separate and unchanged.
