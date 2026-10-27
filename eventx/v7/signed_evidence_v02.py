"""Conservative automatic signed-evidence features for opened V7 development.

This module deliberately abstains unless article and contract text share a supported
macro predicate. It extracts direction relative to canonical YES; it never labels
public surprise and never treats generic trader expectations as prediction-market odds.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re


MONTHS = {
    name: index for index, name in enumerate(
        ("january", "february", "march", "april", "may", "june", "july",
         "august", "september", "october", "november", "december"), 1
    )
}
MONTH_PATTERN = "|".join(MONTHS)


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

    def to_dict(self) -> dict:
        return asdict(self)


def _text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").lower()).strip()


def _months(value: str) -> set[int]:
    return {MONTHS[name] for name in re.findall(rf"\b({MONTH_PATTERN})\b", value)}


def _basis_points(value: str) -> list[int]:
    return [int(x) for x in re.findall(r"\b(\d{1,3})[- ]*(?:basis[ -]?points?|bps?)\b", value)]


def _threshold(value: str) -> float | None:
    match = re.search(r"\b(?:above|more than|greater than)\s*(\d+)\s*k\b", value)
    if match:
        return float(match.group(1)) * 1000
    match = re.search(r"\b(?:above|more than|greater than)\s*(-?\d+(?:\.\d+)?)\s*%?", value)
    return float(match.group(1)) if match else None


def _attribution(article: str) -> str:
    if re.search(r"\b(bank of america|goldman sachs|jpmorgan|analysts?|economists?)\b.*\b(predict|forecast|expect|see)", article):
        return "named_analyst_or_institution"
    if re.search(r"\b(federal reserve|fed chair|bureau of labor statistics|bls|bea|adp)\b", article):
        return "named_official_or_data_source"
    if re.search(r"\b(traders|investors|markets?)\b.*\b(expect|brace|price|bet)", article):
        return "unnamed_market_participants"
    return "unspecified"


def _claim_type(article: str) -> str:
    if re.search(r"\b(reported|added|rose|fell|declined|increased|decreased)\b", article) and re.search(
        r"\b(payroll|unemployment|cpi|pce|inflation|jobs?)\b", article
    ):
        return "observed_measurement"
    if re.search(r"\b(predict(?:ed|s)?|forecast(?:s|ed)?|will be forced|see additional|expected to)\b", article):
        return "forecast"
    if re.search(r"\b(traders|investors|markets?)\b.*\b(expect|brace|price|bet)", article):
        return "general_market_expectation"
    if re.search(r"\b(announced|decided|voted|raised|cut|held|kept)\b", article):
        return "observed_action"
    return "commentary_or_other"


def _explicit_prediction_odds(article: str) -> bool:
    named = bool(re.search(r"\b(polymarket|kalshi|prediction market)\b", article))
    quantified = bool(re.search(r"\b(\d+(?:\.\d+)?\s*%|probability|odds|chance)\b", article))
    return named and quantified


def extract_signed_evidence(
    headline: str | None,
    summary: str | None,
    question: str | None,
) -> SignedEvidence:
    article = _text(" ".join(x for x in (headline, summary) if x))
    contract = _text(question)
    claim_type = _claim_type(article)
    attribution = _attribution(article)
    general_expectation = bool(
        re.search(r"\b(traders|investors|markets?)\b.*\b(expect|brace|price|bet)", article)
    )
    explicit_odds = _explicit_prediction_odds(article)

    def result(applicability: str, direction: int, confidence: float, reason: str) -> SignedEvidence:
        return SignedEvidence(applicability, claim_type, attribution, general_expectation,
                              explicit_odds, direction, confidence, reason)

    # Exclude common lexical traps found in the diagnostic queue.
    explicit_policy_clause = bool(re.search(
        r"\b(federal reserve|fed)\b.{0,80}\b(raise|hike|cut|lower|interest rates?|federal-funds)\b",
        article,
    ))
    if (re.search(r"\b(dividend|buyback|repurchase|stress test|payroll software|stock for retirees)\b", article)
            and not explicit_policy_clause):
        return result("none", 0, 1.0, "corporate or investment context lacks the contract predicate")

    article_months = _months(article)
    contract_months = _months(contract)

    # Payroll threshold statements.
    if "nonfarm payroll" in article and "nonfarm payroll" in contract:
        values = [int(x.replace(",", "")) for x in re.findall(r"\b(\d{2,3}(?:,\d{3})?)\s+(?:nonfarm payroll )?(?:jobs?|payroll)", article)]
        if not values:
            values = [int(x.replace(",", "")) for x in re.findall(r"\badded\s+(\d{2,3}(?:,\d{3})?)\s+jobs", article)]
        threshold = _threshold(contract)
        period_ok = not contract_months or bool(article_months & contract_months)
        if values and threshold is not None and period_ok:
            return result("exact", 1 if values[-1] > threshold else -1, 1.0,
                          "reported payroll value and reference period match the contract threshold")

    # Fed action, hold and path forecasts.
    fed_contract = bool(re.search(r"\b(fed|federal reserve|fomc)\b", contract))
    fed_article = bool(re.search(r"\b(fed|federal reserve|fomc|federal-funds)\b", article)) or bool(
        re.search(r"\bfirst\b.*\b\d{1,3}(?:\s*-?basis[ -]?points?|\s*bps?)\b.*\b(hike|cut)\b", article)
    )
    if fed_contract and fed_article:
        article_hike = bool(re.search(r"\b(hike|raise|increase)\w*\b", article))
        article_cut = bool(re.search(r"\b(cut|lower|decrease)\w*\b", article))
        article_hold = bool(re.search(r"\b(unchanged|hold steady|keep\w* .* unchanged|maintain\w*)\b", article))
        contract_hike = bool(re.search(r"\b(hike|increase)\w*\b", contract)) and "0bps" not in contract
        contract_cut = bool(re.search(r"\b(cut|decrease)\w*\b", contract))
        contract_hold = "0bps" in contract or bool(re.search(r"\b(unchanged|maintain|no change)\b", contract))
        if article_months and contract_months and not (article_months & contract_months):
            # A stated first hike later than a deadline directly opposes a by-deadline hike.
            if contract_hike and "first" in article and min(article_months) > max(contract_months):
                return result("exact", -1, 1.0, "first stated hike occurs after the contract deadline")
            return result("material", 0, 0.5, "Fed claim has a different explicit month or meeting")
        article_bp = _basis_points(article)
        contract_bp = _basis_points(contract)
        if article_hold:
            if "upper bound" in contract:
                threshold = _threshold(contract)
                ranges = re.findall(r"\b(\d+(?:\.\d+)?)\s*%\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*%", article)
                if threshold is not None and ranges:
                    upper = float(ranges[-1][1])
                    return result("exact", 1 if upper > threshold else -1, 1.0,
                                  "stated unchanged range fixes the upper bound relative to the threshold")
            if contract_hold:
                return result("exact", 1, 1.0, "reported hold expectation matches the contract action")
            if contract_hike or contract_cut:
                return result("exact", -1, 1.0, "reported hold expectation opposes the contract action")
        if article_hike:
            if contract_hike:
                exact_bp = not contract_bp or bool(set(article_bp) & set(contract_bp))
                return result("exact" if exact_bp else "material", 1 if exact_bp else 0,
                              1.0 if exact_bp else 0.5, "reported hike claim addresses the Fed predicate")
            if contract_cut or contract_hold:
                return result("material", -1 if contract_cut else 0, 0.6,
                              "reported hike pressure is relevant but does not fix this bucket")
        if article_cut:
            if contract_cut:
                exact_bp = not contract_bp or bool(set(article_bp) & set(contract_bp))
                return result("exact" if exact_bp else "material", 1 if exact_bp else 0,
                              1.0 if exact_bp else 0.5, "reported cut claim addresses the Fed predicate")
            if contract_hike:
                return result("material", -1, 0.6, "reported cut claim opposes a hike predicate")
        if re.search(r"\b(inflation|employment|payroll|jobs?|pce|cpi)\b", article):
            return result("material", 0, 0.4, "macro evidence has a plausible Fed-policy channel without a bucket implication")

    # Same-metric CPI/PCE/unemployment text is context unless a value and period bind.
    metrics = (
        ("core pce", ("core pce",)),
        ("pce", ("pce",)),
        ("cpi", ("cpi", "inflation")),
        ("unemployment", ("unemployment",)),
    )
    for contract_metric, article_terms in metrics:
        if contract_metric in contract and any(term in article for term in article_terms):
            if article_months and contract_months and not (article_months & contract_months):
                return result("none", 0, 0.8, "metric is present but the explicit reference period differs")
            return result("material", 0, 0.4, "same macro metric without an exact threshold implication")

    return result("none", 0, 1.0, "no supported contract-specific macro predicate")
