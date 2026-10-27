"""vNext structured compatibility foundation, not a validated semantic extractor.

Callers supply evidence-backed typed claims. This module never infers certificates
or turns a retrieval score into relevance. Synthetic/development engineering only.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import math

from eventx.v6.contracts import utc

VERSION = 'selective-foundation-0.1'
SUPPORTED_TYPES = {'period_measurement'}


@dataclass(frozen=True)
class Field:
    value: str
    quote: str
    status: str = 'known'

    def valid(self, text):
        return (self.status == 'known' and isinstance(self.value, str)
                and bool(self.value.strip()) and isinstance(self.quote, str)
                and bool(self.quote.strip()) and self.quote in text)


@dataclass(frozen=True)
class Certificate:
    evidence_ref: str
    text_sha256: str
    available_at: str
    valid_from: str
    valid_until: str
    verified: bool = False

    def admits(self, text, decision):
        return (self.verified is True and bool(self.evidence_ref.strip())
                and self.text_sha256 == hashlib.sha256(text.encode()).hexdigest()
                and utc(self.available_at) <= decision
                and utc(self.valid_from) <= decision < utc(self.valid_until))


@dataclass(frozen=True)
class Record:
    identity: str
    text: str
    entity: Field  # typed canonical ID, e.g. company:example; never fuzzy alias
    predicate: Field
    metric: Field
    period: Field  # canonical observation period, not publication quarter
    certificate: Certificate | None
    contract_type: str = 'period_measurement'
    close_at: str | None = None
    evidence_scope: str = 'proposition'


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    article_id: str
    contract_id: str
    version: str = VERSION
    predictive_admitted: bool = False


def compatibility(article, contract, decision_ts):
    """Return compatibility, NOT certified relevance or permission to train.

    This first adapter supports same-period measurements only. Other temporal
    relations (e.g. spot-price evidence for future threshold) await explicit adapters.
    """
    def result(status, reason):
        return Decision(status, reason, article.identity, contract.identity)
    try:
        t = utc(decision_ts)
        for record in (article, contract):
            if not record.identity.strip() or not record.text.strip():
                return result('abstain', 'missing_identity_or_text')
            if record.contract_type not in SUPPORTED_TYPES:
                return result('abstain', 'unsupported_contract_type')
            if not record.certificate or not record.certificate.admits(record.text, t):
                return result('abstain', 'uncertified_or_unavailable_version')
            for field in (record.entity, record.predicate, record.metric, record.period):
                if not field.valid(record.text):
                    return result('abstain', 'missing_conflicting_or_unquoted_semantics')
            if ':' not in record.entity.value or any(not s.strip() for s in record.entity.value.split(':')):
                return result('abstain', 'untyped_entity')
        if contract.close_at is None:
            return result('abstain', 'missing_contract_close')
        if t >= utc(contract.close_at):
            return result('reject', 'contract_closed')
        for name in ('entity', 'predicate', 'metric', 'period'):
            if getattr(article, name).value != getattr(contract, name).value:
                return result('reject', name + '_mismatch')
        if article.evidence_scope != 'proposition':
            return result('abstain', 'background_or_insufficient_evidence')
        return result('compatible_candidate', 'structured_checks_pass_not_relevance_certification')
    except (ValueError, TypeError, AttributeError):
        return result('abstain', 'malformed_input')


def rank_compatible(article, candidates, decision_ts):
    """Filter then sort (Record, finite score) pairs. Never force acceptance.

    Even a compatible candidate still requires a future calibrated acceptance
    policy; deliberately return no supported links in this foundation release.
    """
    diagnostics, ranked = [], []
    seen = set()
    for contract, score in candidates:
        if contract.identity in seen:
            raise ValueError('Duplicate contract identity; reconcile versions explicitly')
        seen.add(contract.identity)
        if not isinstance(score, (int, float)) or not math.isfinite(score):
            raise ValueError('Finite retrieval score required')
        decision = compatibility(article, contract, decision_ts)
        diagnostics.append(decision)
        if decision.status == 'compatible_candidate':
            ranked.append((contract.identity, score))
    ranked.sort(key=lambda pair: (-pair[1], pair[0]))
    return {'status': 'no_supported_match', 'reason': 'acceptance_policy_not_validated' if ranked else 'no_compatible_candidates',
            'ranked_compatible_candidates': ranked, 'supported_links': [], 'diagnostics': diagnostics}
