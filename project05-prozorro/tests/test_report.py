import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from prozorro_compare.reporting import build_report


class ReportTests(unittest.TestCase):
    def test_offline_report_is_deterministic_and_escapes_sources(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); folder=root/'extracts';folder.mkdir()
            x={'source_kind':'real','provenance':{'url':'https://public-api.prozorro.gov.ua/api/2.5/tenders/'+'a'*32},
               'tender':{'id':'a'*32,'tenderID':'UA-2025-01-02-000001-a','title':'<script>alert(1)</script>',
                         'dateCreated':'2025-01-02','status':'cancelled','items':[]},'contract_details':[]}
            (folder/'one.json').write_text(json.dumps(x))
            build_report(folder,root/'a');build_report(folder,root/'b')
            files=list((root/'a').glob('*'))
            self.assertGreater(len(files),5)
            for p in files:self.assertEqual(p.read_bytes(), (root/'b'/p.name).read_bytes())
            html=(root/'a'/'report.html').read_text()
            self.assertNotIn('<script>alert',html)
            self.assertIn('&lt;script&gt;',html)
            result=json.loads((root/'a'/'evaluation.json').read_text())
            self.assertEqual(result['accepted_label_count'],0)
            self.assertFalse(result['validation_gate_met'])

    def test_duplicate_source_lot_fails(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'extracts';folder.mkdir()
            x={'source_kind':'real','provenance':{'url':'https://example.invalid'},'tender':{'id':'a','items':[]}}
            for f in ['a','b']:(folder/(f+'.json')).write_text(json.dumps(x))
            with self.assertRaises(ValueError):build_report(folder,root/'output')

    def test_reviewed_report_narrative_uses_actual_metrics(self):
        from prozorro_compare.reporting import _html,_markdown
        with TemporaryDirectory() as tmp:
            p=Path(tmp)
            counts={'unique_lots':5,'arithmetic_computable':5,'comparison_eligible':5,'real_leads':1}
            summary={'counts':counts,'exclusion_reason_counts':{}}
            evaluation={'accepted_label_count':5,'validation_gate_met':True,'metrics':{'precision':{'estimate':1.0,'denominator':1,'numerator':1,'wilson_95':[0.2,1]}}}
            _markdown(p/'r.md',summary,evaluation)
            _html(p/'r.html',{'records':[],'counts':counts},summary,evaluation)
            for name in ['r.md','r.html']:
                text=(p/name).read_text()
                self.assertNotIn('No independently reviewed',text)
                self.assertNotIn('all annotations',text.lower())
                self.assertIn('precision',text.lower())
                self.assertIn('1.0',text)

if __name__ == '__main__':unittest.main()
