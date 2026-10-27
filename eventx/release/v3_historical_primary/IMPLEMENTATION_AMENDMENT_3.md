# EventX v3 historical implementation amendment 3

Frozen before label construction and before any model result.

The independent development data gate found 204,069 Kalshi warehouse rows with
`count = 0`. A zero-contract record carries no executed payout notional and is not
an executed trade for the quantities defined in the preregistration. Allowing such
rows to update the last-trade price, trade counts, liquidity eligibility, features,
or labels would contradict the protocol's executed-trade measurement definition.

The deterministic normalization policy is therefore:

1. preserve zero-notional rows in the immutable raw Lumid export and report their
   count;
2. exclude rows with Kalshi `count = 0` or Polymarket `size = 0` before every price,
   trade-count, notional, eligibility, feature, volatility, or label calculation;
3. fail closed on negative or non-finite notional; and
4. require every frozen cohort market still to satisfy at least 100 valid executions
   across at least 10 development UTC days after the exclusion.

This is a pre-label source-normalization clarification. It does not alter the frozen
cohort, time split, hypotheses, feature definitions, learner, or promotion gate. If
the original cohort activity thresholds do not survive this stricter normalization,
the development data gate fails and the primary experiment does not proceed.
