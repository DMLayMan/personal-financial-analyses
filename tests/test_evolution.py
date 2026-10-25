"""Knowledge revisions and reports must change for economic inputs, not refresh noise."""
import tempfile
import unittest
from pathlib import Path

from pfa.knowledge import Knowledge
from pfa.platform import Platform
from pfa.research import Research, Conflict
from pfa.markets import MarketBook
from pfa.store import Store
from pfa.assurance import ROOT


class KnowledgeContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.k=Knowledge(Store(Path(self.temp.name)/'test.db'))

    def tearDown(self):self.temp.cleanup()

    def payload(self, **extra):
        return dict(title='现金与资本回报方法',category='method',content='先区分维持与扩张投入，再评估资本回报和净融资需求。',
                    source_url='https://www.berkshirehathaway.com/letters/1986.html',applies_to=['all'],
                    falsifier='不能确定维持投入时保留估计范围，资本需求未知时不称可分配现金。',
                    status='adopted',change_reason='基于原文补充维持投入与资本回报的适用约束。',**extra)

    def test_revision_preserves_history_and_requires_reason(self):
        first=self.k.save(self.payload())
        data=self.payload(entry_id=first['entry_id'],expected_version=1)
        data['content']='修订：将新增租赁承诺和受限现金一并纳入资本要求。'
        second=self.k.save(data)
        self.assertEqual(second['version'],2)
        item=next(e for e in self.k.read()['entries'] if e['entry_id']==first['entry_id'])
        self.assertEqual(len(item['history']),2)
        self.assertEqual(item['history'][0]['content'],first['content'])
        data['change_reason']=''
        with self.assertRaises(ValueError):self.k.save(data)
        with self.assertRaises(Conflict):self.k.save(dict(data,change_reason='再次修订，但使用旧版本，必须阻止覆盖已经更新的方法。'))

    def test_draft_does_not_replace_adopted_method(self):
        first=self.k.save(self.payload())
        data=self.payload(entry_id=first['entry_id'],expected_version=1)
        data.update(status='draft',content='草案：尚待回看原文的新解释，不进入正式采用方法。')
        self.k.save(data)
        active=next(e for e in self.k.applicable('catl','batteries') if e['entry_id']==first['entry_id'])
        self.assertEqual(active['version'],1)
        self.assertFalse(active['method_validated'])


class ReportContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name)/'test.db')
        self.r=Research(self.store);self.r.seed(ROOT/'fixtures/companies.json')
        self.markets=MarketBook(self.store,root=Path(self.temp.name))
        self.platform=Platform(self.r,self.markets)

    def tearDown(self):self.temp.cleanup()

    def save(self,issuer):
        r=self.platform.report(issuer)
        return self.platform.save_report(issuer,dict(dependency_digest=r['dependency_digest'],
            reason='按当前证据及方法保存一版研究草案，保留未知与用途边界。'))

    def test_market_change_marks_saved_report_for_review(self):
        self.markets.capture('hy_oas',[['2026-10-22','3.4']],mode='manual_transcription')
        self.save('catl')
        self.markets.capture('hy_oas',[['2026-10-23','3.7']],mode='manual_transcription')
        report=self.platform.report('catl')
        self.assertIn('market',report['report_delta']['changed_domains'])
        self.assertFalse(report['valuation_gate']['investment_ready'])

    def test_same_observation_refetch_does_not_change_economic_dependencies(self):
        self.markets.capture('hy_oas',[['2026-10-22','3.4']],mode='manual_transcription')
        self.save('catl')
        self.markets.capture('hy_oas',[['2026-10-22','3.4']],mode='manual_transcription')
        self.assertFalse(self.platform.report('catl')['report_delta']['changed_domains'])

    def test_prior_market_revision_is_a_report_change(self):
        self.markets.capture('hy_oas',[['2026-10-21','3.1'],['2026-10-22','3.4']],mode='manual_transcription')
        self.save('catl')
        self.markets.capture('hy_oas',[['2026-10-21','3.2'],['2026-10-22','3.4']],mode='manual_transcription')
        self.assertIn('market',self.platform.report('catl')['report_delta']['changed_domains'])

    def test_method_revision_and_new_event_require_report_review(self):
        self.save('catl')
        k=Knowledge(self.store);entry=next(e for e in k.read()['entries'] if e['entry_id']=='method:cfa')
        data=dict(entry['latest']);data.update(entry_id=entry['entry_id'],expected_version=data['version'],
            content='补充：不能以更多引用代替证据相关性、充分性及可证伪的经营解释。',change_reason='强化当前行业反方审查对证据相关性与解释充分性的要求。')
        k.save(data)
        self.r.command('catl','event',dict(expected_revision=self.r.view('catl')['revision'],title='验收中的待核查事件',
            published_at='2026-10-23',source_url='https://www.catl.com/',mechanism='客户账期变化可能影响营运资本，需原文和回款验证。',unknown='事件线索尚未核验，不直接改变盈利参数。',next_validation='等待原文附注及下一期回款数据。'))
        changed=self.platform.report('catl')['report_delta']['changed_domains']
        self.assertIn('methods',changed);self.assertIn('events',changed)

    def test_missing_model_never_becomes_an_investment_rating(self):
        report=self.platform.report('cmb')
        self.assertFalse(report['valuation_gate']['investment_ready'])
        self.assertIsNone(report['investment_output']['target_price'])
        self.assertEqual(report['investment_output']['rating'],'not_rated')
        self.assertTrue(report['valuation_gate']['missing'])

    def test_stale_dependency_snapshot_is_rejected(self):
        before=self.platform.report('catl')
        self.markets.capture('hy_oas',[['2026-10-22','3.4']],mode='manual_transcription')
        with self.assertRaises(Conflict):
            self.platform.save_report('catl',dict(dependency_digest=before['dependency_digest'],reason='旧页面不能覆盖更新后的市场与方法研究依赖。'))

    def test_cash_signal_is_traceable_and_does_not_become_a_positive_thesis(self):
        report=self.platform.report('catl')
        self.assertEqual(report['report_summary']['business_signal'],'mixed_or_cash_warning')
        ids={f['id'] for f in self.r.view('catl')['quality']['usable']}
        warning=next(f for f in report['findings'] if f['kind']=='monitor')
        self.assertTrue(set(warning['fact_ids'])<=ids)
        self.assertTrue(warning['fact_ids'])
        self.assertIn('尚未',warning['valuation_effect'])

    def test_readable_report_escapes_untrusted_content(self):
        from pfa.report_document import document
        report=self.platform.report('catl')
        report['hypothesis']['question']='<script>untrusted()</script>'
        html=document(report)
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertIn('目标价未形成',html)

    def test_unmapped_new_issuer_exposes_template_gap(self):
        config=dict(self.r.view('msft')['company']);config.pop('id');config.pop('kind');config.pop('issuer')
        with self.store.tx() as db:self.store.add(db,'issuer','newcase',config,'newcase')
        report=self.platform.report('newcase')
        self.assertEqual(report['industry']['id'],'unmapped')
        self.assertFalse(report['valuation_gate']['investment_ready'])

    def test_platform_reference_is_not_presented_as_company_valuation_method(self):
        ids={m['entry_id'] for m in self.platform.report('catl')['methods_applied']}
        self.assertNotIn('method:terminal',ids)
        self.assertNotIn('method:gics',ids)
        self.assertNotIn('method:svb',ids)
        self.assertIn('method:svb',{m['entry_id'] for m in self.platform.report('cmb')['methods_applied']})
