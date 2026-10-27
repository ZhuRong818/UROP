import hashlib
import unittest
from dataclasses import replace
from eventx.v6.selective_vnext import Certificate, Field, Record, compatibility, rank_compatible

TEXT = 'Example reports Q1 2026 revenue fell. Revenue is measured in USD.'
NOW = '2026-05-20T12:00:00Z'


def record(identity):
    proof = Certificate('synthetic:test', hashlib.sha256(TEXT.encode()).hexdigest(),
        '2026-05-20T00:00:00Z', '2026-05-01T00:00:00Z', '2026-06-01T00:00:00Z', True)
    return Record(identity, TEXT, Field('company:example','Example'),
        Field('reports_revenue','revenue'),Field('revenue_USD','USD'),
        Field('2026Q1','Q1 2026'),proof,close_at='2026-05-30T00:00:00Z')


class SelectiveTests(unittest.TestCase):
    def setUp(self): self.a,self.c=record('article:a'),record('contract:c')
    def check(self,a=None,c=None): return compatibility(a or self.a,c or self.c,NOW)
    def test_positive_and_negative_direction(self):
        self.assertEqual(self.check().status,'compatible_candidate') # fell remains relevant
        self.assertFalse(self.check().predictive_admitted)
    def test_wrong_typed_entity(self):
        self.assertEqual(self.check(c=replace(self.c,entity=Field('team:example','Example'))).reason,'entity_mismatch')
    def test_period(self):
        self.assertEqual(self.check(c=replace(self.c,period=Field('2025Q1','Q1 2026'))).reason,'period_mismatch')
    def test_predicate(self):
        self.assertEqual(self.check(c=replace(self.c,predicate=Field('tweet_count','revenue'))).reason,'predicate_mismatch')
    def test_metric(self):
        self.assertEqual(self.check(c=replace(self.c,metric=Field('visits','USD'))).reason,'metric_mismatch')
    def test_fabricated_span(self):
        self.assertEqual(self.check(c=replace(self.c,metric=Field('visits','not in text'))).status,'abstain')
    def test_unknown_or_conflicting(self):
        for status in ('unknown','conflicting'):
            self.assertEqual(self.check(c=replace(self.c,metric=Field('USD','USD',status))).status,'abstain')
    def test_missing_certificate(self):
        self.assertEqual(self.check(c=replace(self.c,certificate=None)).status,'abstain')
    def test_future_revision(self):
        p=replace(self.a.certificate,available_at='2026-05-21T00:00:00Z')
        self.assertEqual(self.check(a=replace(self.a,certificate=p)).status,'abstain')
    def test_changed_text(self):
        self.assertEqual(self.check(a=replace(self.a,text=TEXT+' revised')).status,'abstain')
    def test_half_open_validity(self):
        p=replace(self.a.certificate,valid_until=NOW)
        self.assertEqual(self.check(a=replace(self.a,certificate=p)).status,'abstain')
    def test_closed(self):
        self.assertEqual(self.check(c=replace(self.c,close_at=NOW)).reason,'contract_closed')
    def test_missing_close(self):
        self.assertEqual(self.check(c=replace(self.c,close_at=None)).status,'abstain')
    def test_background(self):
        self.assertEqual(self.check(a=replace(self.a,evidence_scope='background')).status,'abstain')
    def test_unsupported_type(self):
        self.assertEqual(self.check(c=replace(self.c,contract_type='compound')).status,'abstain')
    def test_naive_time(self):
        self.assertEqual(compatibility(self.a,self.c,'2026-05-20').status,'abstain')
    def test_empty_pool(self):
        self.assertEqual(rank_compatible(self.a,[],NOW)['supported_links'],[])
    def test_stable_tie_and_no_auto_accept(self):
        r=rank_compatible(self.a,[(self.c,1),(replace(self.c,identity='contract:b'),1)],NOW)
        self.assertEqual(r['ranked_compatible_candidates'][0][0],'contract:b')
        self.assertEqual(r['supported_links'],[])
    def test_nonfinite(self):
        with self.assertRaises(ValueError): rank_compatible(self.a,[(self.c,float('nan'))],NOW)
    def test_duplicate(self):
        with self.assertRaises(ValueError): rank_compatible(self.a,[(self.c,1),(self.c,2)],NOW)

if __name__=='__main__': unittest.main()
