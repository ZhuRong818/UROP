# EventX v2 category taxonomy and review guide

**Taxonomy version:** `eventx-v2-taxonomy-v1`  
**Permitted inputs:** question, title, description, rules, venue metadata  
**Prohibited inputs:** prices, trades, labels, resolutions not present at the review
timestamp, model predictions, and performance metrics

## Categories

Use exactly one category per market:

- `politics`: elections, nominations, office-holding, legislation, government
  appointments, parties, and public-policy votes;
- `crypto`: cryptocurrency prices, protocols, tokens, blockchains, and crypto
  industry events;
- `sports`: athletic matches, leagues, tournaments, teams, players, and sporting
  awards;
- `macro`: official economic indicators, central banks, interest rates, GDP,
  inflation, unemployment, government debt, and broad commodity benchmarks; or
- `other`: geopolitics, conflict, health, science, entertainment, technology,
  weather, legal cases, and anything not covered above.

Geopolitical office-selection questions remain `politics`; geopolitical conflict
questions are `other`.

## Deterministic first pass

Apply the following precedence:

1. Explicit election, nomination, mayor, governor, president, prime minister,
   parliament, party, cabinet, legislation, or office-holding language → `politics`.
2. Explicit crypto/token/blockchain/protocol language → `crypto`.
3. Explicit league, match, tournament, team, athlete, race, score, championship, or
   sporting-award language → `sports`.
4. Explicit CPI, GDP, unemployment, central-bank, policy-rate, Treasury-yield, or
   official macroeconomic-release language → `macro`.
5. Otherwise → `other`.

An entity name alone must not trigger `sports`. In particular, “Los Angeles” or
another city name does not imply a sports market.

## Independent review

After the deterministic pass:

1. Two reviewers independently label a blind sample of at least 200 candidate
   markets, stratified by proposed category and venue.
2. Reviewers record `label`, `confidence`, and a one-sentence rationale.
3. A third reviewer adjudicates disagreements and all low-confidence cases.
4. Report confusion matrices and per-category precision/recall against the
   adjudicated labels.
5. Acceptance requires overall precision and recall of at least 0.90 and no category
   with at least 20 reviewed cases below 0.80 precision.

If the rule fails, revise it using only the reviewed selection-window metadata,
assign a new taxonomy version, and repeat the audit before development labels are
opened.

## Freeze

The accepted mapping must be stored as a new versioned artifact with market ID,
venue, category, rule version, review status, and provenance. Never modify the v1
cohort file or reuse its defective category tags as v2 ground truth.
