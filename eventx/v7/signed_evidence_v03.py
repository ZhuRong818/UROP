"""Evidence-span-bound macro predicates for opened V7 development.

Version 0.3 is a conservative grammar, not a general entailment model. Direction
is relative to canonical YES. Confidence is a rule weight, not measured accuracy.
An availability year may anchor an explicit month or 'this year'; it never
supplies a missing month. Text/date/status/source validity remain separate gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import re


MONTH_NAMES = ("january", "february", "march", "april", "may", "june", "july",
               "august", "september", "october", "november", "december")
ALIASES = {name: i for i, name in enumerate(MONTH_NAMES, 1)}
ALIASES.update({name[:3]: i for i, name in enumerate(MONTH_NAMES, 1)})
ALIASES["sept"] = 9
MONTH = "(?:" + "|".join(sorted(ALIASES, key=len, reverse=True)) + ")"
FED = r"(?:the\s+)?(?:federal\s+reserve|fed|fomc)"
BP_UNIT = r"(?:basis[ -]points?|bps?)"
NUMBER = r"(?:\d+|zero|no|one|two|three|four|five|six|seven|eight|nine|ten)"
WORDS = {name: i for i, name in enumerate(("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"))}
WORDS["no"] = 0
ACTION = r"(?:hike[sd]?|hiking|rais(?:e[sd]?|ing)|increas(?:e[sd]?|ing)|cuts?|cutting|lower(?:s|ed|ing)?|decreas(?:e[sd]?|ing)|hold(?:s|ing)?|held|keep(?:s|ing)?|kept|maintain(?:s|ed|ing)?|leave|leaves|left)"
RATE_OBJECT = r"(?:(?:its|the|their|benchmark|target|key)\s+)*(?:(?:interest|policy|target)\s+rates?|rates?|(?:benchmark\s+)?federal[ -]funds\s+(?:rate\s+)?(?:target|rate)(?:\s+range)?)(?:\s+target)?"
AUX = r"(?:will|has|had|have|is|are|was|were|be|been|to|expected|predicted|forecast|projected|likely|forced|set|going|not|never|would|may|might|could|won't|doesn't|didn't|can)"
DIRECT = re.compile(rf"\b(?P<actor>{FED})\s+(?P<aux>(?:{AUX}\s+){{0,8}})(?P<verb>{ACTION})\s+(?P<object>{RATE_OBJECT}|(?:by\s+)?\d+(?:\.\d+)?[ -]*{BP_UNIT})\b", re.I)
PERIOD = re.compile(rf"\b(?:in|at|after|following|by|for|during)\s+(?:(?:the|its|their)\s+)?(?P<month>{MONTH})\.?\s*(?P<day>\d{{1,2}}(?:st|nd|rd|th)?)?(?:,?\s*(?P<year>20\d{{2}}))?\b", re.I)
BP = re.compile(rf"(?P<cmp>at\s+least|more\s+than|greater\s+than|over|>|>=)?\s*(?P<value>\d+(?:\.\d+)?)(?P<plus>\+)?[ -]*{BP_UNIT}\b", re.I)
UNCERTAIN = re.compile(r"\b(?:if|unless|may|might|could|would|possibly|possibility|odds|chance|bets?|betting|risk\s+of)\b", re.I)
NEGATED = re.compile(r"\b(?:not|never|no\s+longer|won't|doesn't|didn't|denied|denies|unlikely)\b", re.I)


@dataclass(frozen=True)
class Quantity:
    operator: str
    value: float

    def contains(self, value: float) -> bool:
        return value == self.value if self.operator == "eq" else (value >= self.value if self.operator == "ge" else value > self.value)


@dataclass(frozen=True)
class ContractPredicate:
    kind: str
    action: str | None
    month: int | None
    year: int | None
    quantity: Quantity | None = None
    threshold: float | None = None
    deadline_day: int | None = None


@dataclass(frozen=True)
class BoundClaim:
    action: str
    month: int | None
    year: int | None
    period_kind: str
    period_binding: str
    quantity: Quantity | None
    count: int | None
    upper_rate: float | None
    first_action: bool
    claim_type: str
    attribution_type: str
    evidence_start: int
    evidence_end: int
    evidence_span: str


@dataclass(frozen=True)
class SignedEvidence:
    applicability: str
    claim_type: str
    attribution_type: str
    general_market_expectation: bool
    explicit_prediction_market_odds: bool
    direction: int
    confidence: float
    reason: str
    contract_predicate: ContractPredicate
    bound_claims: tuple[BoundClaim, ...]
    matched_claim_indices: tuple[int, ...] = ()
    public_surprise: None = None
    extractor_version: str = "0.3"

    def to_dict(self) -> dict:
        return asdict(self)


def _number(value: str) -> int:
    return int(value) if value.isdigit() else WORDS[value.lower()]


def _year(available_at: str | datetime | None) -> int | None:
    if isinstance(available_at, datetime):
        return available_at.year
    if available_at:
        return datetime.fromisoformat(available_at.replace("Z", "+00:00")).year
    return None


def _action(verb: str) -> str:
    if re.match(r"hike|hik|rais|increas", verb, re.I):
        return "hike"
    if re.match(r"cut|lower|decreas", verb, re.I):
        return "cut"
    return "hold"


def _quantity(text: str) -> Quantity | None:
    hits = list(BP.finditer(text))
    if len(hits) != 1:
        return None
    m = hits[0]
    comparator = re.sub(r"\s+", " ", (m["cmp"] or "").lower())
    operator = "ge" if m["plus"] or comparator in ("at least", ">=") else "gt" if comparator else "eq"
    return Quantity(operator, float(m["value"]))


def parse_contract(question: str | None) -> ContractPredicate:
    text = question or ""
    lower = text.lower()
    years = set(int(y) for y in re.findall(r"\b20\d{2}\b", text))
    year = next(iter(years)) if len(years) == 1 else None
    month_hits = list(re.finditer(rf"\b({MONTH})\b", lower))
    months = {ALIASES[m[1]] for m in month_hits}
    month = next(iter(months)) if len(months) == 1 else None
    if "nonfarm payroll" in lower and re.search(r"\b(?:us|u\.s\.|united states)\b", lower):
        m = re.search(r"\b(?:above|more than|greater than)\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(k)?\b", lower)
        threshold = float(m[1].replace(",", "")) * (1000 if m and m[2] else 1) if m else None
        return ContractPredicate("us_payroll", None, month, year, threshold=threshold)
    if not re.search(rf"\b{FED}\b", lower):
        return ContractPredicate("unsupported", None, month, year)
    if "upper bound" in lower and re.search(r"federal[ -]funds", lower):
        m = re.search(r"\babove\s*(\d+(?:\.\d+)?)\s*%", lower)
        return ContractPredicate("fed_upper_bound", "hold", month, year, threshold=float(m[1]) if m else None)
    count = re.search(rf"\b(?P<cmp>at least|more than|over)?\s*(?P<n>{NUMBER})\s+(?:{FED})\s+rate\s+cuts?\b", lower)
    if count:
        op = "ge" if count["cmp"] == "at least" else "gt" if count["cmp"] else "eq"
        return ContractPredicate("fed_annual_count", "cut", None, year, Quantity(op, _number(count["n"])))
    verbs = list(re.finditer(r"\b(?:hike|increase|raise|cut|decrease|lower)\w*\b", lower))
    action = _action(verbs[0][0]) if len(verbs) == 1 else None
    amount = _quantity(lower)
    if "no change" in lower or "unchanged" in lower or (amount and amount.operator == "eq" and amount.value == 0):
        action = "hold"
    deadline = re.search(rf"\bby\s+(?P<month>{MONTH})\s+(?P<day>\d{{1,2}})(?:,?\s+20\d{{2}})?", lower)
    if deadline and action:
        return ContractPredicate("fed_deadline", action, month, year, amount, deadline_day=int(deadline["day"]))
    if month is not None and action:
        # If a quantity token exists but cannot be parsed uniquely, fail closed.
        if re.search(BP_UNIT, lower) and amount is None:
            return ContractPredicate("unsupported", action, month, year)
        return ContractPredicate("fed_meeting", action, month, year, amount)
    if month is None and year and action and amount is None:
        return ContractPredicate("fed_annual_any", action, None, year)
    return ContractPredicate("unsupported", action, month, year, amount)


def _segments(text: str):
    start = 0
    for delimiter in re.finditer(r"[.!?;](?:\s+|$)|\n+", text):
        if delimiter.start() > start:
            yield start, text[start:delimiter.start()]
        start = delimiter.end()
    if start < len(text):
        yield start, text[start:]


def _period(text: str, anchor_year: int | None):
    hits = list(PERIOD.finditer(text))
    # Multiple periods in one predicate span require a richer temporal parser.
    if len(hits) == 1:
        m = hits[0]
        explicit_year = int(m["year"]) if m["year"] else None
        other_years = set(int(y) for y in re.findall(r"\b20\d{2}\b", text))
        if len(other_years) > 1 or (explicit_year and other_years != {explicit_year}):
            return None, None, "unknown", "ambiguous_explicit_year"
        year = explicit_year or (next(iter(other_years)) if len(other_years) == 1 else anchor_year)
        binding = "explicit_year" if other_years else "availability_year_anchor" if anchor_year else "missing_year"
        return ALIASES[m["month"].lower()], year, "month", binding
    annual = re.search(r"\b(?:in|during|for|through(?:out)?)\s+(?:calendar\s+)?(20\d{2})\b", text, re.I)
    if annual:
        return None, int(annual[1]), "annual", "explicit_year"
    if re.search(r"\bthis year\b", text, re.I):
        return None, anchor_year, "annual", "availability_year_anchor" if anchor_year else "missing_year"
    return None, None, "unknown", "missing_or_ambiguous_period"


def _mode(text: str) -> str:
    if re.search(r"\b(?:traders|investors|markets?)\b.*\b(?:expect|price|bet)", text, re.I):
        return "general_market_expectation"
    if re.search(r"\b(?:will|expects?|expected|predict\w*|forecast\w*|project\w*|see\w*)\b", text, re.I):
        return "forecast"
    return "observed_action"


def _attribution(text: str) -> str:
    if re.search(r"\b(?:bank of america|goldman sachs|jpmorgan|analysts?|economists?)\b", text, re.I):
        return "named_analyst_or_institution"
    if re.search(r"\b(?:traders|investors|markets?)\b", text, re.I):
        return "unnamed_market_participants"
    if re.search(rf"\b{FED}\b", text, re.I):
        return "named_official_or_data_source"
    return "unspecified"


def _claim(segment: str, offset: int, start: int, end: int, action: str, anchor_year: int | None,
           *, first: bool = False, inherited_mode: str | None = None, inherited_attribution: str | None = None,
           count: int | None = None) -> BoundClaim:
    span = segment[start:end]
    month, year, kind, binding = _period(span, anchor_year)
    quantity = _quantity(span)
    if quantity and quantity.operator == "eq" and quantity.value == 0:
        action = "hold"
    ranges = re.findall(r"(\d+(?:\.\d+)?)\s*%\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*%", span)
    upper = float(ranges[0][1]) if action == "hold" and len(ranges) == 1 else None
    return BoundClaim(action, month, year, kind, binding, quantity, count, upper, first,
                      inherited_mode or _mode(segment[:end]), inherited_attribution or _attribution(segment[:end]),
                      offset+start, offset+end, span)


def _fed_claims(text: str, anchor_year: int | None) -> tuple[BoundClaim, ...]:
    claims = []
    for offset, segment in _segments(text):
        for match in DIRECT.finditer(segment):
            # Bind the action and its complements in this clause, not other verbs
            # or quantities elsewhere in the article.
            end = match.end()
            stop = re.search(r",|\b(?:but|whereas|while|although|and)\b", segment[end:], re.I)
            end = end+stop.start() if stop else len(segment)
            scope = segment[:end]
            if UNCERTAIN.search(scope) or NEGATED.search(scope):
                continue
            action = _action(match["verb"])
            if action == "hold" and not re.search(r"unchanged|steady|maintain|hold|held", segment[match.start():end], re.I):
                continue
            claim = _claim(segment, offset, match.start(), end, action, anchor_year)
            if claim.period_kind != "unknown":
                claims.append(claim)
            # A first action later in the same clause inherits only the bound Fed
            # actor/attribution, and obtains its own size/month.
            tail = segment[end:]
            first = re.match(rf",\s+with\s+the\s+first\s+(?P<bp>\d+(?:\.\d+)?[ -]*{BP_UNIT})\s+(?P<action>hike|cut)\s+in\s+{MONTH}(?:\s+20\d{{2}})?\b", tail, re.I)
            if first and not NEGATED.search(first[0]):
                start = end+first.start()
                finish = end+first.end()
                claims.append(_claim(segment, offset, start, finish, _action(first["action"]), claim.year or anchor_year,
                                     first=True, inherited_mode=claim.claim_type, inherited_attribution=claim.attribution_type))
        # Full-year count forecasts need an explicit total count and Fed actor.
        counts = re.compile(rf"\b(?:(?:expects?|predicts?|forecasts?|projects?)\s+(?:exactly\s+|a\s+total\s+of\s+)?)?(?P<n>{NUMBER})\s+(?:{FED})\s+rate\s+cuts?\s+(?:in|during|for)\s+(?P<year>20\d{{2}})\b", re.I)
        for match in counts.finditer(segment):
            if UNCERTAIN.search(segment) or NEGATED.search(segment):
                continue
            if re.search(r"\b(?:at least|at most|up to|more than|fewer than|additional|another)\s*$", segment[max(0, match.start()-30):match.start()], re.I):
                continue
            if not re.search(r"\b(?:expect\w*|predict\w*|forecast\w*|project\w*)\b", segment[:match.end()], re.I):
                # A cumulative count so far cannot resolve the annual total.
                continue
            claims.append(_claim(segment, offset, match.start(), match.end(), "cut", anchor_year,
                                 count=_number(match["n"]), inherited_mode="forecast"))
    # Repeated headline/summary clauses may give identical evidence implications;
    # preserve all spans and resolve direction disagreements below.
    return tuple(claims)


def _payroll_claims(text: str, anchor_year: int | None) -> tuple[BoundClaim, ...]:
    claims = []
    # Country/source must occur in the measurement clause. Topic-level US stock
    # mentions elsewhere cannot establish the identity of a payroll measurement.
    pattern = re.compile(rf"\b(?P<month>{MONTH})(?:\s+(?P<year>20\d{{2}}))?\s+(?:us\s+)?nonfarm\s+payrolls?\s+(?:added|rose\s+by|increased\s+by)\s+(?P<value>\d+(?:,\d{{3}})*(?:\.\d+)?)(?P<k>k)?\s+jobs\b", re.I)
    for offset, segment in _segments(text):
        if not re.search(r"\b(?:us|u\.s\.|united states|bls|bureau of labor statistics)\b", segment, re.I):
            continue
        if re.search(r"\b(?:private|adp|revised|revision)\b", segment, re.I) or UNCERTAIN.search(segment) or NEGATED.search(segment):
            continue
        for match in pattern.finditer(segment):
            year = int(match["year"]) if match["year"] else anchor_year
            value = float(match["value"].replace(",", ""))*(1000 if match["k"] else 1)
            claims.append(BoundClaim("payroll", ALIASES[match["month"].lower()], year, "month",
                                    "explicit_year" if match["year"] else "availability_year_anchor" if anchor_year else "missing_year",
                                    Quantity("eq", value), None, None, False, "observed_measurement",
                                    "named_official_or_data_source" if re.search(r"\bbls\b|bureau of labor statistics", text, re.I) else "unspecified",
                                    offset+match.start(), offset+match.end(), match[0]))
    return tuple(claims)


def _direction(contract: ContractPredicate, claim: BoundClaim) -> int | None:
    if contract.year is None or claim.year != contract.year:
        return None
    if contract.kind == "us_payroll":
        if claim.action == "payroll" and claim.month == contract.month and contract.threshold is not None:
            return 1 if claim.quantity.value > contract.threshold else -1
        return None
    if contract.kind == "fed_annual_count":
        if claim.period_kind == "annual" and claim.action == "cut" and claim.count is not None:
            return 1 if contract.quantity.contains(claim.count) else -1
        return None
    if contract.kind == "fed_annual_any":
        if claim.action == contract.action and (claim.period_kind == "annual" or claim.month):
            return 1
        return None
    if contract.kind == "fed_deadline":
        # A first action in a later month opposes a by-deadline predicate.
        # No same-month inference without explicit day/meeting identity.
        if claim.action == contract.action and claim.first_action and claim.month and claim.month > contract.month:
            return -1
        if claim.action == contract.action and claim.month and claim.month < contract.month and not contract.quantity:
            return 1
        return None
    if claim.period_kind != "month" or claim.month != contract.month:
        return None
    if contract.kind == "fed_upper_bound":
        if claim.action == "hold" and claim.upper_rate is not None and contract.threshold is not None:
            return 1 if claim.upper_rate > contract.threshold else -1
        return None
    if contract.kind != "fed_meeting":
        return None
    if claim.action == "hold":
        return 1 if contract.action == "hold" else -1
    if contract.action == "hold" or claim.action != contract.action:
        return -1
    if contract.quantity is None:
        return 1
    if claim.quantity is None:
        return None
    if claim.quantity.operator == "eq":
        return 1 if contract.quantity.contains(claim.quantity.value) else -1
    # A lower-bounded claim only supports predicates its entire interval implies.
    if contract.quantity.operator == claim.quantity.operator and contract.quantity.value <= claim.quantity.value:
        return 1
    if claim.quantity.operator == "gt" and contract.quantity.operator == "ge" and claim.quantity.value >= contract.quantity.value:
        return 1
    return None


def extract_signed_evidence(headline: str | None, summary: str | None, question: str | None,
                            *, available_at: str | datetime | None = None) -> SignedEvidence:
    text = "\n".join(value for value in (headline, summary) if value)
    contract = parse_contract(question)
    anchor_year = _year(available_at)
    claims = _payroll_claims(text, anchor_year) if contract.kind == "us_payroll" else _fed_claims(text, anchor_year) if contract.kind.startswith("fed_") else ()
    general = bool(re.search(r"\b(?:traders|investors|markets?)\b.{0,100}\b(?:expect\w*|bet\w*|pric\w*)\b", text, re.I))
    explicit_odds = bool(re.search(r"\b(?:polymarket|kalshi|prediction markets?)\b", text, re.I) and re.search(r"\b(?:odds|probability|chance)\b|\d+(?:\.\d+)?\s*%", text, re.I))
    matches = [(i, _direction(contract, claim)) for i, claim in enumerate(claims)]
    matches = [(i, direction) for i, direction in matches if direction is not None]
    directions = {direction for _, direction in matches}
    if len(directions) == 1:
        indices = tuple(i for i, _ in matches)
        matched = [claims[i] for i in indices]
        mode = matched[0].claim_type if len({c.claim_type for c in matched}) == 1 else "mixed_bound_evidence"
        attribution = matched[0].attribution_type if len({c.attribution_type for c in matched}) == 1 else "mixed_sources"
        return SignedEvidence("exact", mode, attribution, general, explicit_odds, directions.pop(), 1.0,
                              "bound actor/action/period/quantity imply the contract predicate", contract, claims, indices)
    if len(directions) > 1:
        reason = "conflicting bound claims; abstain"
    elif contract.kind == "unsupported":
        reason = "unsupported or ambiguous contract predicate; abstain"
    elif claims:
        reason = "bound claim lacks matching period or exact required quantity/count; abstain"
    else:
        reason = "no unambiguous bound policy or measurement claim; abstain"
    contextual = bool(claims) or (contract.kind.startswith("fed_") and re.search(rf"\b{FED}\b", text, re.I)) or (contract.kind == "us_payroll" and re.search(r"nonfarm payroll", text, re.I))
    return SignedEvidence("material" if contextual else "none", "commentary_or_other", "unspecified",
                          general, explicit_odds, 0, 0.0, reason, contract, claims)
