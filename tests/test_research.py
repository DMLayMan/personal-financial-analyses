import json
import tempfile
import threading
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pfa.models import bank_scenario, earnings_scenario, cumulative_quarter, number
from pfa.research import Research, Conflict
from pfa.server import make_server, ROOT
from pfa.sources import Jobs, validate_url, document_text
from pfa.store import Store
from scripts.validate import walkthrough
from scripts.backup import backup, restore


class ResearchFixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.temp.name)/"research.sqlite3")
        self.r=Research(self.store)
        self.r.seed(ROOT/"fixtures/companies.json")

    def tearDown(self):
        self.temp.cleanup()

    def command(self, ident, action, **data):
        return self.r.command(ident, action, dict(data, expected_revision=self.r.view(ident)["revision"]))

    def initial_conclusions(self):
        return walkthrough(self.r)


class ResearchCase(ResearchFixture):
    def test_six_company_chain_and_gates(self):
        results=self.initial_conclusions()
        self.assertEqual(len(results),6)
        self.assertEqual(sum(row['verified'] for row in results),253)
        for row in results:
            self.assertEqual(row['scenarios'],3)
            self.assertFalse(row['assumptions_confirmed'])
            self.assertGreater(row['open_gaps'],0)
            view=self.r.view(row['issuer'])
            self.assertFalse(view['conclusions'][-1]['stale'])
            self.assertEqual(view['conclusions'][-1]['review_actor'],'implementation_acceptance')
            self.assertIn('无法判断现价',view['conclusions'][-1]['security_direction'])
            model=view['models'][-1]
            self.assertTrue(all(i['fact_id'] for i in model['inputs']))
            if row['issuer']=='cmb':
                self.assertEqual(model['model_type'],'bank_residual_income')
                self.assertEqual(model['inputs'][0]['role'],'common_equity')
            else:
                self.assertEqual(model['model_type'],'earnings_scenario')

    def test_cashflow_alert_and_adjustment_are_traceable(self):
        catl=self.r.view('catl')['quality']['monitors']
        self.assertEqual(len(catl),1)
        self.assertEqual(Decimal(catl[0]['current']),Decimal('1408636000'))
        self.assertEqual(Decimal(catl[0]['prior']),Decimal('21973364000'))
        self.assertLess(Decimal(catl[0]['change']),Decimal('-.93'))
        self.assertEqual(len(catl[0]['fact_ids']),4)
        tencent=self.r.view('tencent')['quality']['monitors']
        self.assertIn('调整后',tencent[0]['title'])

    def test_eps_reconciled_profit_kept_distinct_for_valuation(self):
        model=self.command('byd','model')
        reported=next(i for i in model['inputs'] if i['role']=='net_income')
        valuation=next(i for i in model['inputs'] if i['role']=='valuation_earnings')
        self.assertNotEqual(reported['fact_id'],valuation['fact_id'])
        self.assertEqual(Decimal(valuation['value']),Decimal('32326907000'))
        self.assertTrue(any('EPS勾稽' in s for s in model['warnings']))

    def test_new_event_and_new_assumptions_invalidate_conclusion(self):
        self.initial_conclusions()
        self.command('msft','event',title='资本投入新增披露',source_url='https://www.microsoft.com/investor/',
                     published_at='2026-10-25',mechanism='新增投入→折旧和现金回收→未来利润和股权回报',
                     unknown='仍需核实产能利用率和融资租赁承诺',next_validation='下一期现金流和折旧变化')
        view=self.r.view('msft')
        self.assertTrue(view['conclusions'][-1]['stale'])
        self.assertTrue(any(g['key'].startswith('event:') for g in view['quality']['gaps']))
        with self.assertRaises(Conflict):self.command('msft','publish',reason='新增证据尚未重新建模审查，不应直接发布结论')
        self.command('cost','model')
        view=self.r.view('cost')
        self.assertTrue(view['conclusions'][-1]['stale'])
        self.assertTrue(view['reviews'][-1]['stale'])

    def test_refuted_thesis_changes_action_and_keeps_old_version(self):
        self.initial_conclusions()
        v=self.r.view('byd')
        self.command('byd','review',strongest_counter='新的竞争反证显示原来的量价和盈利机制不成立，需要撤回。',
            response='已区分收入增长与现金利润，不以销量变化直接确认投资价值。',
            falsifier='等待后续分地区车型毛利与库存以及实际回款重新建立判断。',
            verdict='refuted',fact_ids=[v['quality']['usable'][0]['id']])
        c=self.command('byd','publish',reason='反方使原主假设失效，因此保留旧版本并撤回重建。')
        self.assertEqual(c['version'],2)
        self.assertEqual(c['action'],'撤回主假设并补证')
        self.assertIsNotNone(c['previous_id'])
        self.assertEqual(len(self.r.view('byd')['conclusions']),2)

    def test_candidates_not_model_inputs_conflicts_not_averaged(self):
        v=self.r.view('msft')
        source=next(f for f in v['quality']['facts'] if f['metric']=='revenue' and f['period_end']=='2026-06-30')
        payload={k:source[k] for k in ('metric','unit','period_start','period_end','scope','basis','document_id','quote','locator')}
        payload['value']='1'
        new=self.command('msft','fact',**payload)
        model=self.command('msft','model')
        self.assertNotIn(new['id'],[i['fact_id'] for i in model['inputs']])
        self.command('msft','check',fact_id=new['id'],status='verified',reason='核对原始页与期间但此例刻意输入不同数值，用于冲突验收')
        q=self.r.view('msft')['quality']
        self.assertEqual(len(q['conflicts']),1)
        self.assertNotIn(source['id'],[f['id'] for f in q['usable']])
        model=self.command('msft','model')
        self.assertNotIn(new['id'],[i['fact_id'] for i in model['inputs']])
        self.assertNotIn(source['id'],[i['fact_id'] for i in model['inputs']])
        self.command('msft','check',fact_id=new['id'],status='rejected',reason='原文核验发现提取错误，撤回这条候选并保留核验轨迹')
        self.assertEqual(len(self.r.view('msft')['quality']['conflicts']),0)

    def test_rejecting_critical_bank_input_blocks_model(self):
        v=self.r.view('cmb')
        for f in v['quality']['facts']:
            if f['metric']=='common_equity':
                self.command('cmb','check',fact_id=f['id'],status='rejected',reason='本验收撤回所有普通股权益，验证不以总权益冒充')
        m=self.command('cmb','model')
        self.assertEqual(m['status'],'blocked')
        self.assertEqual(m['scenarios'],{})

    def test_review_requires_current_model_and_verified_evidence(self):
        with self.assertRaises(ValueError):self.command('msft','model',confirmed='false',rationale='字符串不能被当成已审议状态，阻止隐式真值转换。')
        with self.assertRaises(ValueError):self.command('msft','publish',reason='没有反方审查和模型时禁止发布结论')
        self.command('msft','model')
        with self.assertRaises(ValueError):
            self.command('msft','review',strongest_counter='缺少事实依据的反方也不应升级成已核验的解释',
                         response='仅提供一段流畅文字不代表已经有有效的实证回应',
                         falsifier='下一报告期核查实际现金和资本投入是否发生改善',verdict='conditional',fact_ids=[])

    def test_revision_conflict_rolls_back(self):
        view=self.r.view('cost');rev=view['revision']
        self.command('cost','model')
        with self.assertRaises(Conflict):self.r.command('cost','model',{'expected_revision':rev})
        self.assertEqual(len(self.r.view('cost')['models']),1)

    def test_seeding_twice_does_not_duplicate(self):
        self.r.seed(ROOT/'fixtures/companies.json')
        self.assertEqual(sum(c['facts'] for c in self.r.dashboard()),253)

    def test_wrong_money_unit_rejected(self):
        f=self.r.view('msft')['quality']['facts'][0]
        with self.assertRaises(ValueError):
            self.command('msft','fact',document_id=f['document_id'],metric='revenue',value='10',unit='ratio',
                         period_end='2026-06-30',period_start='2025-07-01',scope='consolidated',basis='US GAAP',
                         locator='page 1',quote='10')

    def test_missing_adjacent_year_not_reported_as_annual_growth(self):
        view=self.r.view('msft')
        for fact in view['quality']['facts']:
            if fact['metric'] in ('revenue','net_income') and fact['period_end']=='2025-06-30':
                self.command('msft','check',fact_id=fact['id'],status='rejected',reason='隔离库验收：撤回上一年度，检查是否错误将两年累计变化称为年同比。')
        source=view['documents'][0]
        for metric,value in [('revenue','200000000000'),('net_income','80000000000')]:
            item=self.command('msft','fact',document_id=source['id'],metric=metric,value=value,unit='USD',
                 period_start='2023-07-01',period_end='2024-06-30',scope='consolidated',basis='US GAAP',
                 locator='isolated test fixture',quote='synthetic historical record for period-gap test')
            self.command('msft','check',fact_id=item['id'],status='verified',reason='隔离验收的合成历史记录，用于检查期间间隔，不是正式公司数据。')
        model=self.command('msft','model')
        self.assertNotIn('revenue_growth',model['diagnostics'])
        self.assertNotIn('net_income_growth',model['diagnostics'])

    def test_followup_needs_evidence_and_reopens_when_evidence_withdrawn(self):
        view=self.r.view('msft')
        fact=view['quality']['usable'][0]
        with self.assertRaises(ValueError):
            self.command('msft','gap',gap_key='ai_return',disposition='resolved',
                         reason='没有可引用证据时不能仅因为写了文字就关闭研究缺口。',fact_ids=[])
        self.command('msft','gap',gap_key='ai_return',disposition='resolved',
                     reason='这是验收中的有条件补证回应，引用已核验资料并保留经营解释边界，结论仍需审查。',fact_ids=[fact['id']])
        # The former assertion expected closure from any cited fact. That was the
        # audit defect: transcription does not establish semantic sufficiency.
        self.assertIn('ai_return',[g['key'] for g in self.r.view('msft')['quality']['gaps']])
        self.assertEqual(self.r.view('msft')['quality']['resolved_gaps'],[])
        self.command('msft','check',fact_id=fact['id'],status='rejected',reason='验收撤回补证依据，需要重新打开已处理的研究缺口。')
        self.assertIn('ai_return',[g['key'] for g in self.r.view('msft')['quality']['gaps']])

    def test_jobs_deduplicate_fail_visibly_and_recover(self):
        j=Jobs(self.r,ROOT)
        data=dict(url='https://www.tencent.com/not-a-report.pdf',title='补证原文',expected_revision=self.r.view('tencent')['revision'])
        job=j.enqueue('tencent',data)
        data['expected_revision']=self.r.view('tencent')['revision']
        self.assertTrue(j.enqueue('tencent',data)['deduplicated'])
        with patch('pfa.sources.retrieve',side_effect=ValueError('公开源暂不可用')):j.one()
        view=self.r.view('tencent')
        self.assertEqual(view['jobs'][0]['status'],'failed')
        self.assertIn('不可用',view['jobs'][0]['error'])
        j.retry('tencent',dict(job_id=job['id'],expected_revision=view['revision']))
        with patch('pfa.sources.retrieve',side_effect=ValueError('再次失败')):j.one()
        self.assertEqual(self.r.view('tencent')['jobs'][0]['attempts'],2)

    def test_raw_tampering_detected(self):
        raw=ROOT/'data/raw/test-integrity.txt'
        raw.parent.mkdir(parents=True,exist_ok=True);raw.write_text('tampered')
        try:
            with self.assertRaisesRegex(ValueError,'校验值'):
                document_text({'local_path':str(raw),'sha256':'invalid'},ROOT)
        finally:raw.unlink()

    def test_database_backup_recovery(self):
        archive=Path(self.temp.name)/'backup.zip'
        manifest=backup(archive,self.store.path)
        restored=Path(self.temp.name)/'restored'
        restore(archive,restored)
        r=Research(Store(restored/'data/pfa.sqlite3'))
        self.assertEqual(sum(c['facts'] for c in r.dashboard()),253)
        self.assertIn('data/pfa.sqlite3',manifest['files'])


class FinancialLogic(unittest.TestCase):
    def test_flat_profit_valuation_known_annuity(self):
        # Five equal distributions plus an independently computed terminal PV.
        a=dict(growth='0',margin_change='0',terminal_pe='10',discount_rate='.1',payout='1')
        s=earnings_scenario('1000','.1',a)
        expected=sum(Decimal(100)/(Decimal('1.1')**t) for t in range(1,6))+Decimal(1000)/Decimal('1.1')**5
        self.assertAlmostEqual(Decimal(s['total_equity']),expected,places=20)

    def test_bank_roe_equal_cost_is_book_value(self):
        for payout in ['0','.5','1']:
            r=bank_scenario('1000',dict(roe='.12',discount_rate='.12',payout=payout,terminal_growth='.02'))
            self.assertEqual(Decimal(r['total_equity']),Decimal(1000))

    def test_bank_ke_g_and_terminal_retention(self):
        with self.assertRaises(ValueError):bank_scenario('1000',dict(roe='.12',discount_rate='.02',payout='.3',terminal_growth='.02'))
        with self.assertRaises(ValueError):bank_scenario('1000',dict(roe='.01',discount_rate='.12',payout='.3',terminal_growth='.02'))

    def test_cumulative_precision_and_scope(self):
        base=dict(metric='operating_cash_flow',currency='CNY',unit='CNY',scope='consolidated',basis='CAS',period_start='2026-01-01')
        current=dict(base,value='61625487000',period_end='2026-09-30')
        previous=dict(base,value='60216851000',period_end='2026-06-30')
        self.assertEqual(cumulative_quarter(current,previous),'1408636000')
        previous['scope']='parent'
        with self.assertRaises(ValueError):cumulative_quarter(current,previous)

    def test_non_finite_inputs_and_ssrf_rejected(self):
        for value in ['NaN','Infinity','-Infinity','1e999']:
            with self.assertRaises(ValueError):number(value)
        for url in ['http://www.sec.gov','https://127.0.0.1','https://sec.gov.evil.test/a','https://www.sec.gov:9999','file:///etc/passwd']:
            with self.assertRaises(ValueError):validate_url(url)


class HttpAcceptance(ResearchFixture):
    def test_api_real_mutation_csrf_and_local_host(self):
        server=make_server(self.r,Jobs(self.r,ROOT),0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        address=f'http://127.0.0.1:{server.server_port}'
        try:
            bootstrap=json.load(urlopen(address+'/api/bootstrap'))
            self.assertEqual(len(bootstrap['companies']),6)
            body=json.dumps(dict(expected_revision=self.r.view('msft')['revision'])).encode()
            req=Request(address+'/api/companies/msft/model',data=body,headers={'Content-Type':'application/json'})
            with self.assertRaises(HTTPError) as exc:urlopen(req)
            self.assertEqual(exc.exception.code,403)
            req.add_header('X-PFA-Token',bootstrap['csrf'])
            result=json.load(urlopen(req))
            self.assertEqual(len(result['result']['scenarios']),3)
            with self.assertRaises(HTTPError) as exc:urlopen(req)
            self.assertEqual(exc.exception.code,409)
            bad=Request(address+'/api/bootstrap',headers={'Host':'evil.example'})
            with self.assertRaises(HTTPError) as exc:urlopen(bad)
            self.assertEqual(exc.exception.code,403)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)


if __name__=='__main__':unittest.main()
