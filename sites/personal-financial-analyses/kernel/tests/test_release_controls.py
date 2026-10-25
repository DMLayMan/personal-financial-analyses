"""Regressions for defects found in the 0.2 self-review, not return predictions."""
import hashlib
import contextlib
import io
import json
import socket
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

from pfa.research import Research
from pfa.store import Store
from pfa import service
from pfa.models import earnings_scenario
from pfa.assurance import ROOT
from scripts.validate import walkthrough
from scripts import quality_gate


class ReleaseControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.r=Research(Store(Path(self.temp.name)/'research.sqlite3'))
        self.r.seed(ROOT/'fixtures/companies.json')

    def tearDown(self):
        self.temp.cleanup()

    def command(self, issuer, action, **data):
        return self.r.command(issuer, action, dict(data,expected_revision=self.r.view(issuer)['revision']))

    def test_latest_conflict_blocks_instead_of_silently_using_old_year(self):
        v=self.r.view('msft')
        f=next(f for f in v['quality']['usable'] if f['metric']=='revenue' and f['period_end']=='2026-06-30')
        payload={k:f[k] for k in ('document_id','metric','value','unit','period_start','period_end','scope','basis','locator','quote')}
        payload['value']='1'
        new=self.command('msft','fact',**payload)
        self.command('msft','check',fact_id=new['id'],status='verified',reason='隔离库构造同期间矛盾，验证不会回退到旧年度掩盖冲突')
        run=self.command('msft','model')
        self.assertEqual(run['status'],'blocked')
        self.assertEqual(run['scenarios'],{})
        self.assertTrue(any('禁止回退' in s for s in run['issues']))

    def test_raw_integrity_participates_in_model_and_staleness_gates(self):
        raw=ROOT/'data/raw'/('audit-'+Path(self.temp.name).name+'.txt')
        raw.write_text('isolated financial source for control test')
        try:
            with self.r.store.tx() as db:
                doc=self.r.import_document(db,'msft',dict(url='https://www.microsoft.com/audit-only',title='隔离来源',
                    local_path=str(raw),sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),retrieved_at='2026-10-25T00:00:00Z',
                    published_at='2026-07-29',period_end='2026-06-30',currency='USD',basis='US GAAP',scope='consolidated'))
            self.command('msft','fact',document_id=doc['id'],metric='revenue',value='331839000000',unit='USD',
                 period_start='2025-07-01',period_end='2026-06-30',scope='consolidated',basis='US GAAP',locator='synthetic',quote='synthetic')
            before=self.r.view('msft')
            raw.write_text('tampered isolated source')
            after=self.r.view('msft')
            self.assertEqual(after['quality']['source_integrity'][doc['id']],'hash_mismatch')
            run=self.command('msft','model')
            self.assertEqual(run['status'],'blocked')
        finally:raw.unlink(missing_ok=True)

    def test_code_policy_change_invalidates_existing_conclusion(self):
        walkthrough(self.r)
        self.assertFalse(self.r.view('catl')['conclusions'][-1]['stale'])
        with patch('pfa.research.RUNNING_KERNEL','new-calculation-policy'):
            self.assertTrue(self.r.view('catl')['conclusions'][-1]['stale'])

    def test_confirmed_transcription_of_guidance_is_not_historical_actual(self):
        v=self.r.view('msft');new_ids=[]
        for metric in ('revenue','net_income'):
            f=next(f for f in v['quality']['usable'] if f['metric']==metric and f['period_end']=='2026-06-30')
            payload={k:f[k] for k in ('document_id','metric','value','unit','period_start','period_end','scope','basis','locator','quote')}
            payload['evidence_label']='issuer_management_claim'
            new=self.command('msft','fact',**payload);new_ids.append(new['id'])
            self.command('msft','check',fact_id=new['id'],status='verified',reason='仅确认公司说过这句话，不代表它可成为历史实际基线')
        run=self.command('msft','model')
        self.assertFalse(set(new_ids)&{i['fact_id'] for i in run['inputs']})

    def test_unrelated_fact_does_not_close_business_unknown(self):
        view=self.r.view('cost');fact=view['quality']['usable'][0]
        self.command('cost','gap',gap_key='membership_quality',disposition='resolved',
            reason='这条仅是年度收入，不能单独证明续费率和会员质量，属于验收反例。',fact_ids=[fact['id']])
        q=self.r.view('cost')['quality']
        self.assertIn('membership_quality',{g['key'] for g in q['gaps']})
        self.assertFalse(q['resolved_gaps'])

    def test_cashflow_risk_does_not_become_positive_business_conclusion(self):
        walkthrough(self.r)
        view=self.r.view('catl')
        self.assertIn('经营信号混合',view['conclusions'][-1]['operating_direction'])
        self.assertEqual(view['models'][-1]['support_assessment'],'illustrative_only')

    def test_turnaround_path_does_not_treat_loss_as_negative_dividend(self):
        with self.assertRaisesRegex(ValueError,'亏损期'):
            earnings_scenario('1000','-.1',dict(growth='0',margin_change='.2',
                terminal_pe='10',discount_rate='.12',payout='.3'))


class LocalService(unittest.TestCase):
    def test_owned_background_lifecycle_and_application_routes(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=Path(folder)/'runtime';runtime.mkdir()
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            with patch.object(service,'RUNTIME',runtime),patch.object(service,'STATE',runtime/'service.json'):
                try:
                    first=service.start(port,Path(folder)/'isolated.sqlite3')
                    self.assertEqual(first['status'],'ready')
                    self.assertEqual(service.start(port)['pid'],first['pid'])
                    self.assertTrue(service.doctor(port)['passed'])
                    self.assertEqual(service.status()['health']['worker'],'running')
                finally:
                    if service.load() and service.probe(port):service.stop()
                self.assertFalse(service.port_occupied(port))

    def test_wrong_instance_never_stops_another_process(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json'
            path.write_text(json.dumps(dict(port=12345,pid=9999,instance_id='owned')))
            with (patch.object(service,'STATE',path),
                  patch.object(service,'probe',return_value=dict(pid=9999,instance_id='other')),
                  patch.object(service,'port_occupied',return_value=True),
                  patch.object(service.os,'kill') as kill):
                with self.assertRaises(ValueError):service.stop()
                kill.assert_not_called()


class QualityReportControls(unittest.TestCase):
    def test_failed_report_cannot_be_revalidated_as_success(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json'
            path.write_text(json.dumps(dict(source_manifest=quality_gate.source_manifest(),functional_passed=False)))
            with patch.object(sys,'argv',['quality_gate.py','--verify-only','--output',str(path)]),contextlib.redirect_stdout(io.StringIO()):
                self.assertNotEqual(quality_gate.main(),0)

    def test_healthy_old_kernel_cannot_pass_runtime_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json'
            path.write_text(json.dumps(dict(source_manifest=quality_gate.source_manifest(),functional_passed=True)))
            with (patch.object(sys,'argv',['quality_gate.py','--verify-only','--live','--output',str(path)]),
                  patch.object(quality_gate,'doctor',return_value=dict(passed=True)),
                  patch.object(quality_gate,'probe',return_value=dict(kernel_digest='old-running-kernel')),
                  contextlib.redirect_stdout(io.StringIO())):
                self.assertNotEqual(quality_gate.main(),0)


if __name__=='__main__':unittest.main()
