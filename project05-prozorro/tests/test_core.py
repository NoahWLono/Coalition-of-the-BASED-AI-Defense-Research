"""Behavioral tests: hand-calculated inputs, no API or mocked accounting."""
from copy import deepcopy
import json
import unittest

try:
    from prozorro_compare import core
except ImportError:
    core = None


def lot(n='1', price='0.2', source_kind='synthetic'):
    # 100 packs * 500 sheets = 50,000 sheets; amount at 0.2 = 10,000.
    from decimal import Decimal
    return {
        'tender_id': 'tender-' + n, 'lot_id': 'single', 'source_kind': source_kind,
        'status': 'active', 'publication_date': '2025-01-08',
        'items': [{'id': 'paper', 'description': 'A4 80 gsm white 500 sheet packs',
                   'quantity': '100', 'unit': 'pack', 'sheets_per_pack': '500',
                   'pack_size_reviewed': True, 'quantity_version': 'current-v1'}],
        'observations': [{'id': 'contract-1', 'stage': 'contract_current',
                          'amount': str(Decimal(price) * Decimal('50000')),
                          'currency': 'UAH', 'status': 'active', 'item_ids': ['paper'],
                          'quantity_version': 'current-v1', 'quantity_link_reviewed': True,
                          'amendment_reconciled': True}],
        'review': {'annotator_type': 'synthetic_fixture_author', 'reviewed': True,
                   'evidence': ['fixture:known-input'],
                   'evidence_by_gate': {k: ['fixture:known-input'] for k in
                                        ['spec', 'quantity', 'fiscal', 'delivery', 'payment', 'stage']},
                   'spec_key': 'A4-80gsm-grade-A-500', 'fiscal_key': 'UAH-gross-VAT20',
                   'delivery_key': 'delivered-fixed-terms-A', 'payment_key': 'postpay-30d',
                   'vat_included': True, 'net_gross_scope': 'gross'},
    }


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(core, 'core accounting implementation is absent')

    def normalize(self, source):
        return core.normalize_lot(source)

    def test_pack_price_exact_and_raw_strings_retained(self):
        source = lot()
        result = self.normalize(source)
        self.assertEqual(result['quantity_sheets'], '50000')
        self.assertEqual(result['unit_price'], '0.2')
        self.assertTrue(result['comparison_eligible'])
        self.assertEqual(result['items'][0]['quantity'], '100')
        self.assertEqual(result['observations'][0]['amount'], '10000.0')
        self.assertEqual(result['unit_price_fraction'], {'numerator': '1', 'denominator': '5'})
        json.dumps(result, allow_nan=False)

    def test_thousand_pack_and_thousand_sheet_factors(self):
        for unit, size, quantity, expected in [('thousand_pack', '500', '2', '1000000'),
                                                ('thousand_sheet', None, '2', '2000'),
                                                ('sheet', None, '2', '2')]:
            with self.subTest(unit=unit):
                source = lot()
                source['items'][0].update(unit=unit, quantity=quantity, sheets_per_pack=size)
                self.assertEqual(self.normalize(source)['quantity_sheets'], expected)

    def test_thousand_pack_multiplication_keeps_all_input_digits(self):
        source = lot()
        source['items'][0].update(unit='thousand_pack', quantity='1',
                                  sheets_per_pack='123456789012345678901234567890')
        result = self.normalize(source)
        self.assertEqual(result['quantity_sheets'], '123456789012345678901234567890000')

    def test_repeating_unit_price_keeps_exact_rational_pair(self):
        source = lot()
        source['items'][0].update(unit='sheet', quantity='3')
        source['observations'][0]['amount'] = '1'
        result = self.normalize(source)
        self.assertEqual(result['unit_price_fraction'], {'numerator': '1', 'denominator': '3'})
        self.assertTrue(result['unit_price'].startswith('0.333333333333333333'))

    def test_decimal_comma_and_spaces_are_exact(self):
        source = lot()
        source['items'][0].update(unit='sheet', quantity='1 000,5')
        source['observations'][0]['amount'] = '2 001,00'
        result = self.normalize(source)
        self.assertEqual(result['quantity_sheets'], '1000.5')
        self.assertEqual(result['unit_price'], '2')

    def test_invalid_quantity_never_becomes_one(self):
        for bad in [None, '', '0', '-1', 'NaN', 'Infinity', '1,000.5', '1 23', 100.1]:
            with self.subTest(quantity=bad):
                source = lot()
                source['items'][0]['quantity'] = bad
                result = self.normalize(source)
                self.assertIsNone(result['unit_price'])
                self.assertFalse(result['comparison_eligible'])
                self.assertIn('quantity_invalid', result['exclusion_reasons'])

    def test_missing_tax_excludes_but_preserves_arithmetic(self):
        source = lot()
        del source['review']['vat_included']
        result = self.normalize(source)
        self.assertEqual(result['unit_price'], '0.2')
        self.assertFalse(result['comparison_eligible'])
        self.assertIn('fiscal_unknown', result['exclusion_reasons'])

    def test_unknown_delivery_spec_and_payment_never_equal_each_other(self):
        for key, reason in [('delivery_key', 'delivery_unknown'), ('spec_key', 'specification_unknown'),
                            ('payment_key', 'payment_unknown')]:
            source = lot()
            source['review'][key] = None
            result = self.normalize(source)
            self.assertFalse(result['comparison_eligible'])
            self.assertIsNone(result['group_key'])
            self.assertIn(reason, result['exclusion_reasons'])

    def test_multiple_items_and_bundled_services_excluded(self):
        source = lot()
        source['items'].append({'id': 'delivery', 'quantity': '1', 'unit': 'service'})
        result = self.normalize(source)
        self.assertIsNone(result['unit_price'])
        self.assertIn('multiple_items', result['exclusion_reasons'])
        source = lot()
        source['items'][0]['bundled_services'] = True
        self.assertIn('bundled_services', self.normalize(source)['exclusion_reasons'])

    def test_piece_description_does_not_imply_pack(self):
        source = lot()
        source['items'][0]['unit'] = 'piece'
        result = self.normalize(source)
        self.assertIsNone(result['quantity_sheets'])
        self.assertIn('unit_unresolved', result['exclusion_reasons'])

    def test_unreviewed_pack_size_or_unit_conflict_excludes(self):
        source = lot()
        source['items'][0]['pack_size_reviewed'] = False
        self.assertIn('pack_size_unreviewed', self.normalize(source)['exclusion_reasons'])
        source = lot()
        source['items'][0]['unit_conflict'] = True
        self.assertIn('unit_conflict', self.normalize(source)['exclusion_reasons'])

    def test_cancelled_lot_and_contract_not_screened(self):
        source = lot()
        source['status'] = 'cancelled'
        result = self.normalize(source)
        self.assertFalse(result['comparison_eligible'])
        self.assertIn('lot_cancelled', result['exclusion_reasons'])
        source = lot()
        source['observations'][0]['status'] = 'cancelled'
        result = self.normalize(source)
        self.assertIn('no_active_current_contract', result['exclusion_reasons'])
        self.assertEqual(result['observations'][0]['status'], 'cancelled')

    def test_amended_quantity_mismatch_does_not_pair_amount_with_tender(self):
        source = lot()
        source['observations'][0]['quantity_version'] = 'amended-v2'
        result = self.normalize(source)
        self.assertIsNone(result['unit_price'])
        self.assertIn('quantity_version_mismatch', result['exclusion_reasons'])
        source = lot()
        source['observations'][0]['amendment_reconciled'] = False
        self.assertIn('amendment_unreconciled', self.normalize(source)['exclusion_reasons'])

    def test_unreviewed_quantity_link_does_not_produce_price(self):
        source = lot()
        source['observations'][0]['quantity_link_reviewed'] = False
        self.assertIsNone(self.normalize(source)['unit_price'])

    def test_different_stages_do_not_increase_purchase_count(self):
        source = lot()
        for stage in ['estimate', 'bid', 'award', 'amended_contract', 'payment_observed']:
            obs = deepcopy(source['observations'][0])
            obs.update(id=stage, stage=stage, amount='900000')
            source['observations'].append(obs)
        record = self.normalize(source)
        self.assertEqual(record['unit_price'], '0.2')
        self.assertEqual(len(record['observations']), 6)
        self.assertEqual(core.screen([record])['counts']['unique_lots'], 1)

    def test_multiple_active_contracts_excluded_without_selecting_latest(self):
        source = lot()
        second = deepcopy(source['observations'][0])
        second.update(id='contract-2', amount='1')
        source['observations'].append(second)
        result = self.normalize(source)
        self.assertIsNone(result['unit_price'])
        self.assertIn('multiple_active_current_contracts', result['exclusion_reasons'])

    def test_assistant_real_review_provisional_even_with_complete_evidence(self):
        source = lot(source_kind='real')
        source['review']['annotator_type'] = 'assistant'
        result = self.normalize(source)
        self.assertEqual(result['unit_price'], '0.2')
        self.assertFalse(result['comparison_eligible'])
        self.assertIn('independent_human_review_required', result['exclusion_reasons'])
        source['review']['annotator_type'] = 'independent_human'
        self.assertTrue(self.normalize(source)['comparison_eligible'])

    def test_evidence_must_cover_every_gate(self):
        source = lot()
        source['review']['evidence_by_gate']['delivery'] = []
        self.assertIn('delivery_evidence_missing', self.normalize(source)['exclusion_reasons'])

    def test_other_real_currency_excluded(self):
        source = lot(source_kind='real')
        source['review']['annotator_type'] = 'independent_human'
        source['observations'][0]['currency'] = 'USD'
        self.assertIn('currency_out_of_scope', self.normalize(source)['exclusion_reasons'])

    def test_duplicate_lot_or_observation_identifiers_rejected(self):
        record = self.normalize(lot())
        with self.assertRaises(ValueError):
            core.screen([record, deepcopy(record)])
        source = lot()
        source['observations'].append(deepcopy(source['observations'][0]))
        with self.assertRaises(ValueError):
            self.normalize(source)

    def test_missing_publication_month_cannot_group(self):
        source = lot()
        source['publication_date'] = None
        self.assertIn('publication_date_unknown', self.normalize(source)['exclusion_reasons'])


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(core, 'core screening implementation is absent')

    def records(self, prices):
        return [core.normalize_lot(lot(str(i), price)) for i, price in enumerate(prices)]

    def test_small_groups_are_unscreened(self):
        result = core.screen(self.records(['0.2', '0.21', '0.19', '9']))
        self.assertEqual(result['leads'], [])
        self.assertEqual(result['groups'][0]['status'], 'too_small')
        self.assertEqual(result['counts']['screened_lots'], 0)

    def test_robust_two_sided_leads_require_ratio_and_deviation(self):
        result = core.screen(self.records(['0.01', '0.19', '0.2', '0.21', '0.22', '2']))
        self.assertEqual({x['key'] for x in result['leads']}, {'tender-0/single', 'tender-5/single'})
        self.assertEqual({x['direction'] for x in result['leads']}, {'low', 'high'})
        self.assertEqual(result['counts']['screened_lots'], 6)

    def test_zero_mad_uses_declared_ratio_rule(self):
        result = core.screen(self.records(['0.2', '0.2', '0.2', '0.2', '0.4']))
        self.assertEqual(len(result['leads']), 1)
        self.assertEqual(result['leads'][0]['method'], 'zero_mad_ratio_only')
        self.assertTrue(result['groups'][0]['mad_degenerate'])

    def test_groups_do_not_merge_sources_or_fiscal_delivery_months(self):
        records = self.records(['0.2'] * 5)
        other = lot('other', '1', source_kind='real')
        other['review']['annotator_type'] = 'independent_human'
        records.append(core.normalize_lot(other))
        self.assertEqual(len(core.screen(records)['groups']), 2)
        for field, value in [('delivery_key', 'different'), ('fiscal_key', 'different')]:
            source = lot('other', '1')
            source['review'][field] = value
            self.assertEqual(len(core.screen(records[:5] + [core.normalize_lot(source)])['groups']), 2)

    def test_fx_scale_invariance_is_only_mathematical(self):
        original = self.records(['0.01', '0.19', '0.2', '0.21', '0.22', '2'])
        rescaled = self.records(['0.1', '1.9', '2', '2.1', '2.2', '20'])
        self.assertEqual([x['key'] for x in core.screen(original)['leads']],
                         [x['key'] for x in core.screen(rescaled)['leads']])

    def test_sensitivity_table_includes_nine_threshold_pairs(self):
        result = core.screen(self.records(['0.2', '0.2', '0.2', '0.2', '0.4']))
        self.assertEqual(len(result['sensitivity']), 9)
        self.assertTrue(all('lead_count' in row for row in result['sensitivity']))

    def test_no_human_labels_means_null_not_zero(self):
        result = core.evaluate(self.records(['0.2'] * 5), [])
        self.assertFalse(result['validation_gate_met'])
        for name in ['precision', 'false_lead_proportion', 'false_positive_rate', 'false_exclusion_rate']:
            self.assertIsNone(result['metrics'][name]['estimate'])
            self.assertEqual(result['metrics'][name]['denominator'], 0)
        self.assertEqual(result['accepted_label_count'], 0)

    def test_evaluation_denominators_and_wilson_intervals(self):
        records = self.records(['0.01', '0.19', '0.2', '0.21', '0.22', '2'])
        for record in records:
            record['source_kind'] = 'real'
        labels = [{'key': r['key'], 'annotator_type': 'independent_human',
                   'evidence': ['review:holdout'], 'comparable': True,
                   'unusual': i == 5} for i, r in enumerate(records)]
        result = core.evaluate(records, labels)
        self.assertEqual(result['metrics']['precision']['numerator'], 1)
        self.assertEqual(result['metrics']['precision']['denominator'], 2)
        self.assertEqual(result['metrics']['false_positive_rate']['denominator'], 5)
        self.assertEqual(result['metrics']['false_positive_rate']['numerator'], 1)
        self.assertEqual(result['metrics']['false_exclusion_rate']['denominator'], 6)
        self.assertEqual(result['metrics']['false_exclusion_rate']['numerator'], 0)
        self.assertAlmostEqual(result['metrics']['precision']['estimate'], 0.5)
        self.assertLess(result['metrics']['precision']['wilson_95'][0], 0.5)
        self.assertGreater(result['metrics']['precision']['wilson_95'][1], 0.5)

    def test_synthetic_and_assistant_labels_do_not_validate_real_data(self):
        records = self.records(['0.2'] * 5)
        labels = [{'key': r['key'], 'annotator_type': 'independent_human',
                   'evidence': ['review:holdout'], 'comparable': True, 'unusual': False}
                  for r in records]
        self.assertEqual(core.evaluate(records, labels)['accepted_label_count'], 0)
        records[0]['source_kind'] = 'real'
        labels[0]['annotator_type'] = 'assistant'
        self.assertEqual(core.evaluate(records, labels)['accepted_label_count'], 0)

    def test_duplicate_and_unknown_holdout_labels_rejected(self):
        records = self.records(['0.2'] * 5)
        with self.assertRaises(ValueError):
            core.evaluate(records, [{'key': 'unknown'}])
        with self.assertRaises(ValueError):
            core.evaluate(records, [{'key': records[0]['key']}, {'key': records[0]['key']}])


if __name__ == '__main__':
    unittest.main()
