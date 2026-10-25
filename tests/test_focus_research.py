"""Independent arithmetic and publication boundary checks for the dated study.

Selected source answers were registered before report rendering. These checks do
not validate attribution, forecasts or investment performance.
"""
from datetime import date,timedelta
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pfa.publications import publication

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'research/2026-10-25'
def read(name):return json.loads((DATA/name).read_text())

class FocusResearch(unittest.TestCase):
    def test_byd_cash_and_share_bridges(self):
        b=read('byd-agent.json')
        facts={(f['metric'],f['period']):D(f['value']) for f in b['facts'] if f.get('value') is not None}
        v=lambda k:facts[k,'2026H1']
        cal=b['calculations'];cv=lambda k:D(cal[k]['value'])
        self.assertEqual(v('CFO')-v('cash_capex'),D('-7368322000'))
        self.assertEqual(v('working_capital_inventory_effect')+v('working_capital_receivables_effect')+v('working_capital_payables_effect'),D('-14940484000'))
        self.assertEqual(cv('cashflow_ending_cash_bridge'),D('55619085000'))
        self.assertEqual(cv('TTM_EPS_numerator'),D('29310241000'))
        mixed=D('81.42')*D('5433797565')+D('71.6')*D('.85696')*D('3683400000')
        self.assertEqual(mixed,D('668427092564.70'))
        self.assertEqual(cv('mixed_class_group_marketcap_CNY'),mixed)
        self.assertNotEqual(mixed,D('71.6')*D('9117197565')*D('.85696'))

    def test_continuous_ttm_and_no_future_financial_inputs(self):
        expected={'NVDA':'7.91','AVGO':'7.83','VRT':'4.42','ETN':'9.83'}
        for r in read('infra-valuation-inputs.json'):
            eps=r['eps_inputs'];self.assertEqual(len(eps),4)
            self.assertEqual(sum(D(str(x['val'])) for x in eps),D(expected[r['symbol']]))
            for x in eps:self.assertLessEqual(x['filed'],'2026-10-25')
            for left,right in zip(eps,eps[1:]):
                self.assertEqual(date.fromisoformat(left['end'])+timedelta(days=1),date.fromisoformat(right['start']))
            for item in r.values():
                if isinstance(item,dict) and item.get('value') is not None and 'inputs' in item:
                    a,b,c=item['inputs'];self.assertEqual(D(str(a['val']))+D(str(b['val']))-D(str(c['val'])),D(item['value']))

    def test_market_identity_dates_and_currency(self):
        m=read('market-snapshot.json');self.assertFalse(m['realtime']);self.assertFalse(m['history_point_in_time'])
        self.assertEqual(len(m['rows']),40)
        for r in m['rows']:
            self.assertEqual(r['status'],'observed');self.assertEqual(r['observation_date'],'2026-10-23')
            self.assertTrue(D(r['price'])>0)
            self.assertEqual(r['currency'],'HKD' if r['symbol'].endswith('.HK') else 'CNY' if r['symbol'].endswith(('.SS','.SZ')) else 'USD')

    def test_unit_cost_includes_capital_and_utilization(self):
        g=read('unit-economic-diagnostics.json')['gpu']
        crf=D('.1')*D('1.1')**3/(D('1.1')**3-1)
        total=D(50000)*crf+D(1500)+D('1.2')*D('1.2')*8760*D('.08')
        self.assertAlmostEqual(D(g['annual_cost']),total,places=15)
        self.assertTrue(D('.64')<D(g['breakeven_paid_utilization'])<D('.65'))
        self.assertTrue(total/(8760*D('.4'))>D(6))
        self.assertTrue(total/(8760*D('.8'))<D('3.3'))

    def test_reports_bound_to_catalog_and_failure_routes(self):
        catalog=json.loads((ROOT/'knowledge/research-publications.json').read_text())
        self.assertFalse(catalog['investment_ready'])
        for r in catalog['publications']:
            body,policy=publication(r['route'])
            self.assertEqual(hashlib.sha256(body).hexdigest(),r['sha256'])
            self.assertIn("script-src 'sha256-",policy)
            self.assertIn('未来',body.decode());self.assertIn('反',body.decode())
        for route in ['/research/../../.env','/research/byd.html','/research/%2e%2e/pfa/store.py']:
            self.assertIsNone(publication(route))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'knowledge').mkdir();(root/'research').mkdir()
            (root/'knowledge/research-publications.json').write_text(json.dumps({'publications':[{'route':'/research/test.html','path':'research/test.html','sha256':'0'*64}]}))
            (root/'research/test.html').write_text('<html>tampered</html>')
            with patch('pfa.publications.ROOT',root),self.assertRaisesRegex(ValueError,'摘要'):
                publication('/research/test.html')

    def test_capital_identity_and_unresolved_evidence_preserved(self):
        a=read('ai-apps-agent.json');byname={r['name']:r for r in a['model_capital_status']}
        self.assertIn('Nonlisted',byname['OpenAI']['status'])
        pltr=next(x for x in a['sources'] if x['id']=='pltr-q2')
        self.assertIn('sec.gov',pltr['url']);self.assertIn('shell',pltr['prior_attempt']['retrieval_status'])
        self.assertTrue(read('adversarial-review.json')['unresolved_priority'])
        html=(DATA/'ai-full-stack.html').read_text()
        for phrase in ['2027','私募','并入','未取得','不是预测','融资','普通股']:
            self.assertIn(phrase,html)

if __name__=='__main__':unittest.main()
