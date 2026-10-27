import unittest
from eventx.v6.field_aware import fields, query, hypothesis, top_set


def card(q, rules=''):
    return {'contract_id': 'test', 'question': q,
            'recovered_rule_evidence': [{'text': rules}] if rules else []}


class FieldAwareTests(unittest.TestCase):
    def test_boilerplate_invariance(self):
        q = 'Will Bitcoin reach $100000?'
        self.assertEqual(query(fields(card(q))), query(fields(card(q, 'Binance candle. ' * 4))))

    def test_exclusion_priority(self):
        f = fields(card('Question?', 'Official acts do not count. Resolution source is Binance.'))
        self.assertEqual([s['role'] for s in f['rule_spans']], ['exclusion', 'source_boilerplate'])
        for s in f['rule_spans']:
            self.assertEqual(s['quote'], s['source']['text'][s['start']:s['end']])

    def test_country_not_team(self):
        r = hypothesis({'headline': 'Alcoa signs Norway power agreement'}, fields(card('Will Norway win the 2026 FIFA World Cup?')))
        self.assertEqual(r['status'], 'abstain')

    def test_sports_context_not_settlement(self):
        r = hypothesis({'headline': 'Argentina wins World Cup match'}, fields(card('Will Argentina win the 2026 FIFA World Cup?')))
        self.assertEqual(r['status'], 'event_context_hypothesis')
        self.assertFalse(r['settlement_evidence'])

    def test_asset_context_not_strike(self):
        r = hypothesis({'headline': 'Company sells Bitcoin holdings'}, fields(card('Will Bitcoin hit $150k?')))
        self.assertEqual(r['status'], 'asset_context_hypothesis')
        self.assertFalse(r['predictive_admitted'])

    def test_stock_target_not_asset_measurement(self):
        r = hypothesis({'headline': 'Strategy Bitcoin playbook', 'summary': 'Citi cuts stock price target to $136'}, fields(card('Will Bitcoin hit $150k?')))
        self.assertEqual(r['status'], 'abstain')

    def test_speech_not_actor(self):
        r = hypothesis({'headline': 'Trump signs quantum orders'}, fields(card('Will Trump say "Goat" before July?')))
        self.assertEqual(r['reason'], 'target_utterance_absent')

    def test_keyword_not_attribution(self):
        r = hypothesis({'headline': 'Trump watched a goat'}, fields(card('Will Trump say "Goat" before July?')))
        self.assertEqual(r['status'], 'abstain')

    def test_tie(self):
        self.assertEqual(top_set([{'contract_id': 'a', 's': .03}, {'contract_id': 'b', 's': .03+1e-17}], 's'), ['a', 'b'])

    def test_empty(self):
        self.assertEqual(top_set([], 's'), [])

    def test_sidebar(self):
        r = hypothesis({'headline': 'Other news', 'summary': 'Related Articles Bitcoin price rises'}, fields(card('Will Bitcoin hit $150k?')))
        self.assertEqual(r['status'], 'abstain')

    def test_unknown_abstains(self):
        self.assertEqual(hypothesis({'headline': 'Something'}, fields(card('Unknown?')))['status'], 'abstain')


if __name__ == '__main__':
    unittest.main()
