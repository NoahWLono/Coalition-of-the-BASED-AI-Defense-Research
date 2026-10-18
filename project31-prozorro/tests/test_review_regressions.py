import unittest
from prozorro_compare.core import example_lot,normalize_lot


class ReviewRegressions(unittest.TestCase):
    def test_source_vat_flag_overrules_conflicting_review(self):
        r=example_lot();r['observations'][0]['vat_included']=False
        n=normalize_lot(r)
        self.assertFalse(n['comparison_eligible'])
        self.assertIn('fiscal_source_conflict',n['exclusion_reasons'])

    def test_explicit_lot_conflict_fails_closed(self):
        r=example_lot();r['lot_link_conflict']=True
        n=normalize_lot(r)
        self.assertFalse(n['comparison_eligible'])
        self.assertIn('lot_link_conflict',n['exclusion_reasons'])

if __name__=='__main__':unittest.main()
