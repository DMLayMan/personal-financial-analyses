"""The browser adapter must retain the exact research semantics."""
import tempfile,unittest
from pathlib import Path
from pfa.cloud_bridge import BrowserBridge,CachedResponse
from pfa.store import Store
from pfa.research import Research
from pfa.assurance import ROOT

class CloudBridgeContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.bridge=BrowserBridge(Path(self.temp.name)/'db.sqlite3')
        self.bridge.research.seed(ROOT/'fixtures/companies.json')
    def tearDown(self):self.temp.cleanup()
    def test_six_company_reports_use_same_financial_kernel(self):
        for issuer in ('msft','cost','tencent','byd','catl','cmb'):
            actual=self.bridge.request('/api/reports/'+issuer)
            self.assertEqual(actual['status'],200)
            self.assertEqual(actual['body']['financials'],self.bridge.platform.report(issuer)['financials'])
            self.assertFalse(actual['body']['valuation_gate']['investment_ready'])
            self.assertIsNone(actual['body']['investment_output']['target_price'])
    def test_mutation_keeps_version_conflict_and_immutable_report(self):
        report=self.bridge.request('/api/reports/catl')['body']
        data=dict(dependency_digest=report['dependency_digest'],reason='浏览器适配必须保留旧报告与研究用途限制，不得升级投资评级。')
        saved=self.bridge.request('/api/reports/catl/snapshot','POST',data)
        self.assertEqual(saved['status'],200)
        version=self.bridge.request('/api/report-versions/'+saved['body']['result']['id'])
        self.assertIn('研究草案',version['body']['html'])
        stale=self.bridge.request('/api/reports/catl/snapshot','POST',dict(data,dependency_digest='old'))
        self.assertEqual(stale['status'],409)
    def test_unknown_route_does_not_mutate(self):
        self.assertEqual(self.bridge.request('/api/not-real')['status'],404)
        self.assertEqual(self.bridge.request('/api/not-real','POST',{})['status'],404)
    def test_failed_cached_request_never_supplies_source_bytes(self):
        with self.assertRaises(OSError):CachedResponse(dict(error='来源访问限制'))
    def test_snapshot_is_consistent_sqlite(self):
        target=Path(self.temp.name)/'consistent.sqlite3';self.bridge.snapshot(target)
        import sqlite3
        with sqlite3.connect(target) as db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
