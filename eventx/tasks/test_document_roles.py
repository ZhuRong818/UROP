import unittest
from eventx.v6.document_roles import fields, hypothesis
from eventx.tasks.test_field_aware import card


class DocumentRoleTests(unittest.TestCase):
    def check(self, q, headline, summary='', expected='abstain'):
        a = {'headline': headline, 'summary': summary}
        r = hypothesis(a, fields(card(q)))
        self.assertEqual(r['status'], expected)
        self.assertFalse(r['predictive_admitted'])
        for e in r['evidence']:
            self.assertEqual(a[e['field']][e['start']:e['end']], e['quote'])

    def test_host(self):
        self.check('Will Mexico win the 2026 FIFA World Cup?', 'Mexico will let Iran team use Tijuana for World Cup matches')

    def test_team(self):
        self.check('Will Iran win the 2026 FIFA World Cup?', 'Mexico will let Iran team use Tijuana for World Cup matches', expected='event_context_hypothesis')

    def test_cross_field(self):
        self.check('Will Argentina win the 2026 FIFA World Cup?', 'Google Search hits record during World Cup drama', "Argentina’s late win drove search usage", 'event_context_hypothesis')

    def test_stage(self):
        self.check('Will Argentina reach the Semifinals at the 2026 FIFA World Cup?', 'World Cup drama', "Argentina's win drove searches", 'event_context_hypothesis')

    def test_figurative(self):
        self.check('Will Bitcoin hit $150k?', 'Buying Time, or Why Strategy Stock Is Gaining After Unveiling a New Bitcoin Playbook', 'Citi cuts stock price target to $136')

    def test_variant_host(self):
        self.check('Will Canada win the 2026 FIFA World Cup?', 'Canada hosts Brazil team for football training')

    def test_variant_team(self):
        self.check('Will Brazil win the 2026 FIFA World Cup?', 'Canada hosts Brazil team for football training', expected='event_context_hypothesis')

    def test_variant_asset(self):
        self.check('Will Ethereum hit $9000?', 'Fund sold Ethereum', expected='asset_context_hypothesis')

    def test_variant_figurative(self):
        self.check('Will Ethereum hit $9000?', 'Buying time for Ethereum software developers')

    def test_unrelated_country(self):
        self.check('Will Norway win the 2026 FIFA World Cup?', 'World Cup preview', 'Norway signs power agreement')

    def test_sidebar(self):
        self.check('Will Brazil win the 2026 FIFA World Cup?', 'World Cup overview', 'Related Articles Brazil won a match')

    def test_stock(self):
        self.check('Will Bitcoin hit $150k?', 'Bitcoin software firm raises stock price target')


if __name__ == '__main__':
    unittest.main()
