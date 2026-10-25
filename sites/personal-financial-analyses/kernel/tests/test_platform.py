"""Platform hierarchy, honest capability labels and industry report dependencies."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pfa.platform import Platform
from pfa.research import Research
from pfa.markets import MarketBook
from pfa.store import Store
from pfa.assurance import ROOT
from scripts.validate import walkthrough


class PlatformContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.r=Research(Store(Path(self.temp.name)/'test.db'))
        self.r.seed(ROOT/'fixtures/companies.json')
        self.platform=Platform(self.r,MarketBook(self.r.store,root=Path(self.temp.name)))

    def tearDown(self):
        self.temp.cleanup()

    def test_three_axes_are_first_class(self):
        data=self.platform.overview()
        self.assertEqual([a['id'] for a in data['axes']],['foundation','markets','cases'])
        self.assertGreaterEqual(len(data['workflow']),9)
        self.assertTrue(data['review']['verdict'])
        self.assertTrue(data['roadmap'])

    def test_planned_agent_capabilities_not_claimed_running(self):
        data=self.platform.overview()
        self.assertFalse(data['agent_execution']['autonomous_research'])
        self.assertFalse(data['agent_execution']['external_llm_configured'])
        for agent in data['agents']:
            self.assertTrue(all(agent.get(k) for k in ('inputs','outputs','current','guard')))

    def test_sources_and_method_references_are_traceable(self):
        data=self.platform.overview()
        ids={r['id'] for r in data['references']}
        for principle in data['principles']:
            self.assertTrue(set(principle['refs'])<=ids)
        for ref in data['references']+data['sources']:
            self.assertTrue(ref['url'].startswith('https://'))
        self.assertIn('三层',self.platform.library('architecture')['text'])
        with self.assertRaises(ValueError): self.platform.library('../../pfa/store.py')

    def test_each_case_has_industry_driver_and_report_contract(self):
        data=self.platform.industries()
        covered=[c for i in data['industries'] for c in i['companies']]
        self.assertCountEqual(covered,['msft','cost','tencent','byd','catl','cmb'])
        for issuer in covered:
            report=self.platform.report(issuer)
            self.assertTrue(report['industry']['kpis'])
            self.assertTrue(report['industry']['bridge'])
            self.assertTrue(report['macro_channels'])
            self.assertGreaterEqual(len(report['sections']),9)
            self.assertFalse(report['research_decision_ready'])

    def test_report_preserves_stale_and_unvalidated_states(self):
        walkthrough(self.r)
        before=self.platform.report('catl')
        self.assertFalse(before['conclusion']['stale'])
        self.assertFalse(before['research_decision_ready'])
        self.assertEqual(before['model']['support_assessment'],'illustrative_only')
        with patch('pfa.research.RUNNING_KERNEL','changed-policy'):
            after=self.platform.report('catl')
        self.assertTrue(after['conclusion']['stale'])
        self.assertTrue(after['needs_review'])

    def test_verified_management_claim_is_not_reported_as_historical_actual(self):
        f=next(f for f in self.r.view('msft')['quality']['usable'] if f['metric']=='revenue')
        payload={k:f[k] for k in ('document_id','metric','value','unit','period_start','period_end','scope','basis','locator','quote')}
        payload['evidence_label']='issuer_management_claim'
        payload['basis']='管理层说法转录，非报告实际'
        payload['expected_revision']=self.r.view('msft')['revision']
        new=self.r.command('msft','fact',payload)
        self.r.command('msft','check',dict(fact_id=new['id'],status='verified',reason='核对公司说过这句话，不把口头说法变成历史实际',expected_revision=self.r.view('msft')['revision']))
        self.assertNotIn(new['id'],[f['id'] for f in self.platform.report('msft')['financials']])
