# KOL–Market Blind Review Guide

## Purpose

Decide whether each tweet is relevant to the specific prediction-market question shown
with it. Review the tweet using only the question, tweet text, author, and timestamp in
the blinded sample.

Do not open the internal key, the previous audit, the matching code, or rule-v2 results
until all labels have been submitted. Do not use later events or the eventual market
resolution.

## Labels

Enter exactly one value in `review_label`:

- `relevant` — the tweet contains information that could reasonably update the
  probability of the stated market outcome at the time it was posted.
- `not_relevant` — the overlap is generic, tangential, about a different event, or
  insufficient to update that outcome.
- `uncertain` — the text is genuinely ambiguous or lacks enough context for a reliable
  binary decision. Use this sparingly; uncertain cases will be adjudicated separately.

Enter `high`, `medium`, or `low` in `review_confidence`. Add one short,
tweet-specific sentence in `review_rationale`. Enter your identifier in `reviewer`.

## Relevant cases

Label a tweet `relevant` when it does at least one of the following:

- Directly discusses whether the market outcome will occur.
- Reports a poll, election result, candidacy, endorsement, nomination, succession,
  leadership change, or credible odds update involving the named contender.
- Reports a concrete military, political, health, shipping, or market development
  directly bearing on the event.
- Provides evidence that the outcome has occurred, is progressing, is delayed, is less
  likely, or has explicitly not occurred. Negative evidence and reported absence can be
  relevant.
- Discusses the exact event without naming every entity in the question, when the event
  identity is still unambiguous.

The tweet need not be true or from an authoritative source. Judge whether its content is
about the outcome, not whether you personally believe it.

## Not-relevant cases

Label a tweet `not_relevant` when it only:

- Shares a person, country, title, date, or generic keyword with the question.
- Describes a politician's routine duties or unrelated controversy without connecting
  it to the election, nomination, or succession in question.
- Discusses a different election, conflict, disease, market, location, or time period.
- Mentions broad background conditions without a concrete connection to the outcome.
- Contains an isolated name, list entry, advertisement, or URL with too little text to
  identify an outcome-relevant claim.

## Edge-case rules

1. Review each question–tweet pair independently. The same tweet may be relevant to one
   market and irrelevant to another.
2. Use only information available in the tweet at its timestamp. Do not use hindsight.
3. Opinions, forecasts, and quoted odds are relevant when they explicitly concern the
   outcome. Generic praise, criticism, or commentary is not.
4. For candidate markets, merely holding the current office or appearing in political
   news is not enough. Look for electoral, nomination, polling, succession, or
   candidacy context.
5. For event-status markets, both positive and negative status updates count. For
   example, traffic remaining blocked or a public figure failing to appear can update
   the probability of a future recovery or appearance.
6. When the tweet discusses the precise event but the likely direction of its effect is
   unclear, label it `relevant`; direction is not part of this task.
7. Use `uncertain` only when reasonable reviewers could not decide from the supplied
   text. Explain what information is missing.

## Review procedure

1. Open `kol_association_blind_review.jsonl`.
2. Read the market question first, then the complete tweet.
3. Fill `review_label`, `review_confidence`, `review_rationale`, and `reviewer`.
4. Do not reorder rows or change `audit_id`.
5. Confirm that every row has a label and rationale.
6. Return the completed JSONL without opening
   `kol_association_blind_key.jsonl`.

Example completed fields:

```json
{
  "review_label": "relevant",
  "review_confidence": "high",
  "review_rationale": "Reports a new poll measuring the named candidate in the specified election.",
  "reviewer": "reviewer_02"
}
```
