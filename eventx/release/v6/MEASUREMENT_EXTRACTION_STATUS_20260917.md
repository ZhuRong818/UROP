# Measurement extraction 0.1 — development engineering

Implemented quoted entity, metric, predicate and explicit year-qualified quarter
extraction in `eventx/v6/measurement_extractor.py`. Typed alias collisions and multiple
quarters/metrics remain conflicting; absent fields remain unknown. Same local claim
support yields a direct *candidate*, never an independently validated link. Entity-only
coverage yields background; contradictions and insufficient evidence are distinct.
Threshold quotation/settlement entailment is not required. No certificate is fabricated.

32 synthetic tests passed across extraction and compatibility foundations. The debug
runner reads only the already-opened blank40-case packet, not reviewer labels, and
preserves frozen artifacts. It constructs exact-name hypotheses only from the narrow
`Will <company> report` grammar; the resulting registry contains just Vail Resorts Inc.
No automatic shortening to Vail Resorts or external alias inference is performed.

Result:1 mismatch candidate,39 insufficient-evidence cases,0 predictive admissions.
Canonical outputs: `data/v6/measurement_extraction_debug_20260917/`. These are debug
counts, not accuracy, recall, quality-gate results or independent evaluation. The
extractor is currently far too narrow for the intended broad-market task.

## Remaining work and honest stopping point

Extraction is lexical, not general semantic understanding. Clause splitting is
conservative and can miss abbreviations; fiscal/calendar equivalence, unit conversion,
coreference, multiple claims, event deadlines and price-threshold relations are not
implemented. Question-only development parsing does not replace full subtitle/rule
semantics. Existing temporal foundation remains separate; no end-to-end source
certification or automatic production acceptance is claimed.

Next engineering: build evidence-backed entity aliases and explicit per-type adapters
from opened development metadata, then preserve subtitle/rule provenance and bind
claims to measurement periods. Test useful positive coverage as well as rejection.
No new review batch is requested now.

Do NOT freeze the fresh audit yet: the method is not stable/useful enough, and precision,
minimum coverage/yield, independent sampling scope and hard annotation budget remain
unapproved. Keep all40 cases as development; preserve the previous nonpass. Once the
method is ready, freeze code and those choices before touching new reference labels.
