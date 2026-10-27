"""As-of metadata and fold-scoped, pre-window semantic feature materialization.

This reference adapter intentionally refuses the legacy discovery feature arrays.
Callers must supply immutable content versions and certified stream completeness.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from eventx.features.v2_1_association import associate, market_spec
from eventx.features.v4_news import market_relative_novelty
from .splits import HORIZON_US, MINUTE_US, RowIndex


def require_timestamps(*values):
    if any(isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer))
           for value in values):
        raise ValueError("Availability and event times require integer UTC microseconds")


@dataclass(frozen=True)
class Metadata:
    market: str
    version: str
    available: int
    valid_from: int
    valid_until: int | None
    question: str
    category: str
    is_open: bool
    scheduled_terminal: int | None = None

    def __post_init__(self):
        require_timestamps(self.available, self.valid_from)
        if self.valid_until is not None:
            require_timestamps(self.valid_until)
            if self.valid_until <= self.valid_from:
                raise ValueError("Empty metadata validity interval")
        if self.scheduled_terminal is not None:
            require_timestamps(self.scheduled_terminal)
        if not self.market or not self.version or not self.question:
            raise ValueError("Metadata identity/version/question required")


def metadata_at(versions, market, at):
    known = [m for m in versions if m.market == market and m.available <= at
             and m.valid_from <= at and (m.valid_until is None or at < m.valid_until)]
    if not known:
        return None
    known.sort(key=lambda m: (m.available, m.valid_from, m.version))
    if len(known) > 1 and known[-1].available == known[-2].available:
        raise ValueError("Ambiguous simultaneous metadata versions")
    return known[-1]


@dataclass(frozen=True)
class Article:
    identity: str  # frozen online dedup identity; never selected using future rows
    published: int
    first_seen: int
    content_available: int  # availability of THIS exact text version, not original ID
    text: str
    families: frozenset[str]  # verified warm-up associations; not used as model inputs

    def __post_init__(self):
        require_timestamps(self.published, self.first_seen, self.content_available)
        if not self.identity or not self.text:
            raise ValueError("Article identity and immutable content required")

    @property
    def available(self):
        return max(self.published, self.first_seen, self.content_available)


@dataclass(frozen=True)
class Decision:
    market: str
    time: int
    label_end: int
    family: str
    family_verified: bool
    market_values: tuple[float, ...]
    market_available: int  # latest availability across causal market input windows
    coverage_complete: bool  # news/market history incl. seven-day novelty warm-up

    def __post_init__(self):
        require_timestamps(self.time, self.label_end, self.market_available)


class SemanticEncoder:
    def __init__(self, cutoff, components=64, min_df=3, max_df=.995):
        self.cutoff, self.components = cutoff, components
        self.vectorizer = TfidfVectorizer(
            lowercase=True, strip_accents="unicode", ngram_range=(1, 2),
            min_df=min_df, max_df=max_df, max_features=50000,
            sublinear_tf=True, norm="l2", dtype=np.float32)

    def fit(self, articles, train_families):
        selected = [a for a in articles if a.available < self.cutoff
                    and a.families and a.families.issubset(train_families)]
        if not selected:
            raise ValueError("No pre-window, training-family semantic corpus")
        matrix = self.vectorizer.fit_transform(a.text for a in selected)
        if min(matrix.shape) <= self.components:
            raise ValueError("Insufficient warm-up corpus for frozen semantic dimension")
        self.svd = TruncatedSVD(n_components=self.components, n_iter=5, random_state=73)
        self.svd.fit(matrix)
        self.fit_ids = tuple(a.identity for a in selected)
        self.fit_latest = max(a.available for a in selected)
        return self

    def transform(self, texts, decision_time):
        if decision_time < self.cutoff:
            raise ValueError("Semantic model was unavailable at prediction time")
        return normalize(self.svd.transform(self.vectorizer.transform(texts)))


@dataclass
class FeatureBatch:
    market: np.ndarray
    residual: np.ndarray
    exposed: np.ndarray


class PITSource:
    """Small/reference raw-to-features adapter; not a bulk warehouse implementation.

    fit(train_ids) is called anew at every nesting level. Corpus selection is
    training-family-only and precedes ALL scored rows. Caps fit on train only.
    Metadata-unknown/closed rows fail admission; terminal-unknown is explicit.
    """

    def __init__(self, decisions, metadata, articles, semantic_cutoff,
                 semantic_options=None, association=None, residual_kind="news"):
        self.decisions, self.metadata = tuple(decisions), tuple(metadata)
        self.cutoff = semantic_cutoff
        self.semantic_options = semantic_options or {}
        if residual_kind not in {"news", "context", "timing"}:
            raise ValueError("Unknown residual kind")
        self.residual_kind = residual_kind
        self.association = association or (
            lambda meta, text: bool(associate(market_spec(meta.question, meta.category), text)[0]))
        # Online first-version policy. Later duplicates/revisions never rewrite an
        # earlier identity. Ambiguous ties fail rather than pick revised text.
        earliest = {}
        for a in sorted(articles, key=lambda a: (a.available, a.identity)):
            old = earliest.get(a.identity)
            if old is not None and old.available == a.available and old != a:
                raise ValueError("Ambiguous simultaneous article versions")
            earliest.setdefault(a.identity, a)
        self.articles = tuple(earliest.values())
        self.index = RowIndex(
            np.array([d.time for d in self.decisions], dtype=np.int64),
            np.array([d.label_end for d in self.decisions], dtype=np.int64),
            np.array([d.family for d in self.decisions]),
            np.array([d.family_verified for d in self.decisions]))
        market_families = {}
        row_keys = set()
        for d in self.decisions:
            if market_families.setdefault(d.market, d.family) != d.family:
                raise ValueError("A market cannot change event family between rows")
            if (d.market, d.time) in row_keys:
                raise ValueError("Duplicate market/decision row")
            row_keys.add((d.market, d.time))
            meta = metadata_at(self.metadata, d.market, d.time)
            if (d.time < self.cutoff + HORIZON_US or d.market_available > d.time
                    or not d.coverage_complete or meta is None or not meta.is_open
                    or not np.isfinite(d.market_values).all()):
                raise ValueError(f"Row fails PIT/eligibility/coverage admission: {d.market}@{d.time}")

    def fit(self, train_ids):
        return FittedPIT(self, np.asarray(train_ids, dtype=int))


class FittedPIT:
    def __init__(self, source, train_ids):
        if not len(train_ids):
            raise ValueError("Cannot fit features without training rows")
        self.source = source
        self.train_ids = train_ids.copy()
        self.encoder = SemanticEncoder(source.cutoff, **source.semantic_options).fit(
            source.articles, frozenset(source.index.family[train_ids]))
        raw = self._raw(train_ids)
        self.count_cap = float(np.quantile(raw[2][:, 3], .99))
        self.provenance = {
            "semantic_cutoff": source.cutoff,
            "semantic_fit_latest": self.encoder.fit_latest,
            "semantic_article_ids": self.encoder.fit_ids,
            "train_only_count_cap": self.count_cap,
        }

    def _raw(self, ids):
        market, news, gate = [], [], []
        s = self.source
        for i in ids:
            d = s.decisions[int(i)]
            meta = metadata_at(s.metadata, d.market, d.time)
            terminal = (0.0 if meta.scheduled_terminal is None else
                        np.log1p(max(0, (meta.scheduled_terminal - d.time) / MINUTE_US)))
            market.append([*d.market_values, terminal, float(meta.scheduled_terminal is None)])
            history = []
            for a in s.articles:
                if a.available > d.time:
                    break
                # Restrict semantic association to the metadata actually known
                # when this article arrived, and unchanged question semantics.
                at_article = metadata_at(s.metadata, d.market, a.available)
                if (at_article is not None and at_article.is_open
                        and (at_article.question, at_article.category) == (meta.question, meta.category)
                        and self.source.association(at_article, a.text)):
                    history.append(a)
            recent = [j for j, a in enumerate(history) if a.available > d.time - HORIZON_US]
            gate.append(bool(recent))
            if not recent:
                news.append([0, 0, 0, 0, 0])
                continue
            vectors = self.encoder.transform([a.text for a in history], d.time)
            question = self.encoder.transform([meta.question], d.time)[0]
            relevance = np.clip(vectors @ question, 0, 1)
            novelty = market_relative_novelty(
                np.array([a.available for a in history], dtype=np.int64), vectors)
            quality = relevance * novelty
            maximum = float(np.max(quality[recent]))
            news.append([maximum, float(quality[recent[-1]]),
                         (d.time - history[recent[-1]].available) / MINUTE_US,
                         len(recent), maximum * terminal])
        return np.asarray(market), np.asarray(gate, dtype=bool), np.asarray(news)

    def transform(self, ids):
        market, exposed, news = self._raw(ids)
        news[:, 3] = np.log1p(np.minimum(news[:, 3], self.count_cap))
        residual = market.copy()
        if self.source.residual_kind == "timing":
            residual = np.column_stack([market, news[:, 2:4]])
        elif self.source.residual_kind == "news":
            residual = np.column_stack([market, news])
        return FeatureBatch(market, residual, exposed)
