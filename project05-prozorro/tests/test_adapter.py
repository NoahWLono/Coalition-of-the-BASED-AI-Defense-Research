import unittest
from prozorro_compare.adapter import adapt, item_input


class AdapterTests(unittest.TestCase):
    def fixture(self):
        item = {'id':'i', 'description':'Папір А4 500 арк.', 'quantity':'10', 'unit':{'code':'PK','name':'пачка'}}
        return {'source_kind':'real', 'provenance':{'url':'https://example.invalid/tender','retrieved_at':'2026-10-18'},
                'tender':{'id':'t','tenderID':'UA-2025-02-01-000001-a','dateCreated':'2025-02-01','status':'complete','items':[item],
                'value':{'amount':'2000','currency':'UAH'},'contracts':[{'id':'c','status':'active','value':{'amount':'1800','currency':'UAH'}}]},
                'contract_details':[]}

    def test_ambiguous_piece_is_not_pack(self):
        x = self.fixture()['tender']['items'][0]; x['unit']={'code':'H87','name':'штука'}
        self.assertEqual(item_input(x,'tender')['unit'], 'unresolved')

    def test_explicit_pack_and_size(self):
        x = item_input(self.fixture()['tender']['items'][0], 'v1')
        self.assertEqual(x['unit'], 'pack'); self.assertEqual(x['sheets_per_pack'], '500')

    def test_contract_without_items_cannot_borrow_quantity(self):
        result = adapt(self.fixture())
        self.assertFalse(result['observations'][-1]['quantity_link_reviewed'])
        self.assertEqual(len(result['observations']), 2)

    def test_authoritative_contract_items_replace_tender_quantity(self):
        d = self.fixture(); c = dict(d['tender']['contracts'][0]); c['items'] = [dict(d['tender']['items'][0],quantity='7')]; c['changes']=[{'id':'change'}]
        d['contract_details']=[{'contract':c,'provenance':{'url':'https://example.invalid/contract'}}]
        result=adapt(d)
        self.assertEqual(result['items'][0]['quantity'],'7')
        self.assertEqual(result['observations'][-1]['stage'],'amended_contract')
        self.assertFalse(result['observations'][-1]['amendment_reconciled'])

    def test_amount_paid_is_separate_and_not_zero_when_absent(self):
        d=self.fixture();c=dict(d['tender']['contracts'][0]);c['amountPaid']={'amount':'1700','currency':'UAH'}
        d['contract_details']=[{'contract':c,'provenance':{}}]
        result=adapt(d)
        self.assertEqual([x['amount'] for x in result['observations'] if x['stage']=='payment_observed'], ['1700'])
        self.assertEqual([x for x in adapt(self.fixture())['observations'] if x['stage']=='payment_observed'], [])

    def test_annotations_are_explicitly_assistant(self):
        d=adapt(self.fixture())
        self.assertEqual(d['review']['annotator_type'],'assistant')
        self.assertFalse(d['review']['reviewed'])

    def test_ambiguous_pack_size_is_unresolved(self):
        for description in ['Папір 500-600 арк.', 'Папір не менше 500 арк.', 'Папір 1 500 арк.', 'Папір 500,5 арк.']:
            x=self.fixture()['tender']['items'][0];x['description']=description
            self.assertFalse(item_input(x,'v1')['pack_size_reviewed'],description)

    def test_explicit_lot_mismatch_blocks_arithmetic(self):
        d=self.fixture();d['tender']['lots']=[{'id':'wanted'}]
        c=dict(d['tender']['contracts'][0]);c['lotID']='other'
        c['items']=[dict(d['tender']['items'][0],relatedLot='other')]
        d['contract_details']=[{'contract':c,'provenance':{}}]
        r=adapt(d)
        self.assertFalse(r['observations'][-1]['quantity_link_reviewed'])
        self.assertTrue(r['lot_link_conflict'])

    def test_failed_authoritative_contract_read_does_not_fallback(self):
        d=self.fixture();d['tender']['contracts'][0]['items']=d['tender']['items']
        d['contract_details']=[{'contract':None,'provenance':{'url':'https://example.invalid/contracts/c','status':404}}]
        r=adapt(d)
        self.assertFalse(r['observations'][-1]['quantity_link_reviewed'])
        self.assertTrue(r['current_contract_state_unavailable'])

if __name__ == '__main__': unittest.main()
