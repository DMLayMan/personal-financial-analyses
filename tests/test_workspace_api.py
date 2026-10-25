"""New layers are reachable and local mutations keep existing request protection."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from pfa.research import Research
from pfa.store import Store
from pfa.markets import MarketBook
from pfa.sources import Jobs
from pfa.server import make_server,ROOT


class WorkspaceAPI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.r=Research(Store(Path(self.temp.name)/'test.db'))
        self.r.seed(ROOT/'fixtures/companies.json')
        self.server=make_server(self.r,Jobs(self.r,ROOT),0,markets=MarketBook(self.r.store,root=Path(self.temp.name)))
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.worker.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.worker.join();self.temp.cleanup()

    def read(self,path):
        with urlopen(self.base+path,timeout=5) as r: return json.load(r)

    def test_three_layers_reports_and_whitelisted_documents(self):
        self.assertEqual(len(self.read('/api/platform')['axes']),3)
        self.assertTrue(self.read('/api/markets')['entries'])
        self.assertEqual(len(self.read('/api/industries')['industries']),6)
        for issuer in ('msft','cost','tencent','byd','catl','cmb'):
            self.assertEqual(self.read('/api/reports/'+issuer)['company']['id'],issuer)
        self.assertIn('三层',self.read('/api/library/architecture')['text'])
        with self.assertRaises(HTTPError):self.read('/api/library/secrets')
        with urlopen(self.base+'/workspace.js') as r: self.assertEqual(r.status,200)

    def test_market_refresh_requires_token_and_deduplicates(self):
        def post(token):
            return urlopen(Request(self.base+'/api/markets/refresh',data=b'{}',headers={
                'Content-Type':'application/json','X-PFA-Token':token}),timeout=5)
        with self.assertRaises(HTTPError) as error:post('wrong')
        self.assertEqual(error.exception.code,403)
        token=self.read('/api/bootstrap')['csrf']
        with post(token) as r:first=json.load(r)['result']
        with post(token) as r:second=json.load(r)['result']
        self.assertEqual(first['id'],second['id'])
        self.assertTrue(second['deduplicated'])

    def test_knowledge_and_report_snapshot_roundtrip_with_frozen_document(self):
        token=self.read('/api/bootstrap')['csrf']
        def post(path,data):
            with urlopen(Request(self.base+path,data=json.dumps(data).encode(),headers={
                'Content-Type':'application/json','X-PFA-Token':token}),timeout=5) as r:return json.load(r)
        original=self.read('/api/reports/catl')
        saved=post('/api/reports/catl/snapshot',dict(dependency_digest=original['dependency_digest'],
            reason='在隔离验收库保存当前证据研究更新，不升级为投资评级。'))['result']
        html=self.read('/api/report-versions/'+saved['id'])['html']
        self.assertIn('未评级',html);self.assertIn('目标价未形成',html)
        self.assertIn('单季经营现金流显著下降',html)
        self.assertTrue(self.read('/api/knowledge')['entries'])
        self.assertFalse(self.read('/api/information')['delivery']['continuous_realtime'])
        self.assertIn('<!doctype html>',self.read('/api/reports/catl/document')['html'])
        with urlopen(self.base+'/reports/catl') as r:
            self.assertIn('text/html',r.headers['Content-Type'])
            self.assertIn("default-src 'none'",r.headers['Content-Security-Policy'])
            self.assertIn('sha256-',r.headers['Content-Security-Policy'])
            self.assertNotIn('unsafe-inline',r.headers['Content-Security-Policy'])

    def test_new_mutations_keep_local_token_protection(self):
        for path in ('/api/knowledge','/api/information/refresh','/api/reports/catl/snapshot'):
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.base+path,data=b'{}',headers={'Content-Type':'application/json'}))
            self.assertEqual(caught.exception.code,403)


if __name__=='__main__':unittest.main()
