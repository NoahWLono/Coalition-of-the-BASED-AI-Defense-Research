import unittest
from prozorro_compare.acquire import sanitize, candidate_scope, safe_url


class AcquisitionTests(unittest.TestCase):
    def example(self):
        return {'id': 'a'*32, 'tenderID': 'UA-2025-02-03-000001-a',
                'dateCreated': '2025-02-03T12:00:00+02:00', 'title': 'Папір А4',
                'procuringEntity': {'name': 'Ліцей', 'contactPoint': {'email': 'private@example.com'}},
                'items': [{'id': 'i', 'description': 'Папір А4 80 г 500 арк', 'quantity': '10',
                           'unit': {'code': 'NMP', 'name': 'пачка'},
                           'deliveryAddress': {'streetAddress': 'PRIVATE'},
                           'deliveryLocation': {'latitude': 1}}],
                'contracts': [{'id': 'c', 'suppliers': [{'name': 'PERSON'}],
                               'value': {'amount': '1250.10', 'currency': 'UAH'}}]}

    def test_scope_requires_civilian_and_period(self):
        d = self.example()
        self.assertEqual(candidate_scope(d), [])
        d['procuringEntity']['name'] = 'Військовий ліцей'
        self.assertIn('excluded_buyer_scope', candidate_scope(d))
        d['dateCreated'] = '2024-12-31T12:00:00+02:00'
        self.assertIn('outside_publication_period', candidate_scope(d))

    def test_unknown_buyer_is_excluded(self):
        d = self.example(); d['procuringEntity']['name'] = 'Невідома організація'
        self.assertIn('civilian_buyer_unverified', candidate_scope(d))

    def test_projection_removes_contacts_locations_suppliers(self):
        import json
        result = sanitize(self.example())
        text = json.dumps(result)
        for secret in ('private@example.com', 'PRIVATE', 'PERSON', 'latitude', 'procuringEntity'):
            self.assertNotIn(secret, text)
        self.assertEqual(result['contracts'][0]['value']['amount'], '1250.10')

    def test_api_origin_and_path_are_pinned(self):
        self.assertTrue(safe_url('https://public-api.prozorro.gov.ua/api/2.5/tenders/'+'a'*32))
        for url in ['http://public-api.prozorro.gov.ua/api/2.5/tenders',
                    'https://evil.example/api/2.5/tenders',
                    'https://public-api.prozorro.gov.ua.evil/api/2.5/tenders',
                    'https://public-api.prozorro.gov.ua/api/2.5/../private']:
            self.assertFalse(safe_url(url))

    def test_missing_creation_is_not_modification_date(self):
        d = self.example(); del d['dateCreated']; d['dateModified'] = '2025-02-03'
        self.assertIn('missing_publication_date', candidate_scope(d))

    def test_nonpaper_or_multilot_excluded(self):
        d = self.example(); d['items'][0]['description'] = 'Ноутбук'
        self.assertIn('no_a4_paper_item', candidate_scope(d))
        d = self.example(); d['lots'] = [{'id': '1'}, {'id': '2'}]
        self.assertIn('multiple_lots_not_acquired', candidate_scope(d))

    def test_restricted_records_are_excluded(self):
        d = self.example(); d['config'] = {'restricted': True}
        self.assertIn('restricted_record', candidate_scope(d))

    def test_single_paper_item_can_use_tender_a4_description(self):
        d = self.example(); d['items'][0]['description'] = 'Папір'
        self.assertEqual(candidate_scope(d), [])

    def test_civilian_court_and_district_administration(self):
        for name in ['Районний суд', 'Районна державна адміністрація']:
            d = self.example(); d['procuringEntity']['name'] = name
            self.assertEqual(candidate_scope(d), [])

    def test_public_tender_identifier_date_must_agree(self):
        d = self.example(); d['tenderID'] = 'UA-2024-02-03-000001-a'
        self.assertIn('publication_date_conflict', candidate_scope(d))

    def test_sensitive_free_text_is_not_acquired(self):
        d=self.example();d['items'][0]['description']+=' contact private@example.com'
        self.assertIn('sensitive_free_text',candidate_scope(d))


if __name__ == '__main__':
    unittest.main()
