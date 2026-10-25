"""Predefined units, gaps, timing and failure contracts for the market layer."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pfa.markets import MarketBook, statistics, parse_yahoo, curve
from pfa.store import Store
from unittest.mock import patch


class MarketLogic(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.book = MarketBook(Store(self.root/'test.db'), root=self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_rate_changes_use_basis_points(self):
        result = statistics([['2026-10-21', '5.13'], ['2026-10-22', '4.96']], 'percent_rate')
        self.assertEqual(result['change'], '-17.00')
        self.assertEqual(result['change_unit'], 'bp')
        self.assertEqual(statistics([['2026-10-21','100'],['2026-10-22','102']], 'index')['change'], '2.00')

    def test_missing_values_not_forward_filled(self):
        result = statistics([['2026-10-20', '1'], ['2026-10-21', None], ['2026-10-22', '3']], 'fx')
        self.assertIsNone(result['change'])
        self.assertIsNone(result['history'][1][1])
        self.assertIsNone(statistics([['2026-10-20','1'],['2026-10-21',None]], 'fx')['value'])
        self.assertIsNone(statistics([['2026-10-20','1']], 'index')['change'])

    def test_failed_refresh_preserves_old_snapshot_and_labels_it(self):
        self.book.capture('us10y', [['2026-10-21','5.13'],['2026-10-22','4.96']], mode='manual_transcription')
        self.book.failure('us10y', 'read timeout')
        entry = self.book.entry('us10y')
        self.assertEqual(entry['value'], '4.96')
        self.assertEqual(entry['date'], '2026-10-22')
        self.assertEqual(entry['last_attempt']['status'], 'failed')
        self.assertIn('timeout', entry['last_attempt']['error'])
        self.assertFalse(entry['realtime'])

    def test_curve_uses_common_dates_and_preserves_input_dates(self):
        result = curve([['2026-10-21','5.13'],['2026-10-22','4.96']], [['2026-10-21','4.81']])
        self.assertEqual(result, [['2026-10-21','32.00']])
        self.assertEqual(curve([['2026-10-22','4.96']], [['2026-10-22',None]]), [['2026-10-22',None]])

    def test_future_quotes_and_missing_closes_are_not_prices(self):
        body = json.dumps({'chart': {'error': None, 'result': [{'meta': {'exchangeTimezoneName':'UTC'},
            'timestamp': [1792540800,1792627200,4070908800],
            'indicators': {'quote': [{'close': [100,None,999]}]}}]}}).encode()
        points, meta = parse_yahoo(body, asof=date(2026,10,25))
        self.assertEqual(len(points), 2)
        self.assertIsNone(points[-1][1])

    def test_tampered_snapshot_is_quarantined(self):
        self.book.capture('us10y', [['2026-10-22','4.96']], mode='manual_transcription')
        entry = self.book.entry('us10y')
        (self.root/entry['provenance']['local_path']).write_text('tampered')
        entry = self.book.entry('us10y')
        self.assertEqual(entry['state'], 'integrity_failed')
        self.assertIsNone(entry['value'])

    def test_macro_refresh_does_not_enter_company_source_queue(self):
        from pfa.research import Research
        from pfa.sources import Jobs
        self.book.enqueue()
        self.assertFalse(Jobs(Research(self.book.store), self.root).one())

    def test_threshold_is_review_condition_not_company_direction(self):
        self.book.capture('us10y', [['2026-10-21','5.13'],['2026-10-22','4.96']], mode='manual_transcription')
        entry=self.book.entry('us10y')
        self.assertTrue(entry['attention']['triggered'])
        self.assertIn('未经校准', entry['attention']['limit'])
        self.assertNotIn('rating', entry)

    def test_market_raw_payload_is_included_in_backup_and_restore(self):
        from scripts import backup
        self.book.capture('us10y', [['2026-10-22','4.96']], mode='manual_transcription')
        path=self.book.entry('us10y')['provenance']['local_path']
        archive=self.root/'backup.zip'
        with patch.object(backup,'ROOT',self.root):
            backup.backup(archive,db_path=self.book.store.path)
        backup.restore(archive,self.root/'restored')
        self.assertTrue((self.root/'restored'/path).is_file())

    def test_wrong_symbol_response_is_rejected(self):
        raw=json.dumps({'chart':{'result':[{'meta':{'symbol':'WRONG','exchangeTimezoneName':'UTC','instrumentType':'INDEX'},
             'timestamp':[1792540800],'indicators':{'quote':[{'close':[100]}]}}],'error':None}}).encode()
        from io import BytesIO
        with patch('pfa.markets.urlopen',return_value=BytesIO(raw)):
            self.assertIsNone(self.book.refresh_metric('sp500'))
        self.assertIsNone(self.book.entry('sp500')['value'])
        self.assertEqual(self.book.entry('sp500')['last_attempt']['status'],'failed')

    def test_invalid_numeric_response_is_preserved_as_failure_evidence(self):
        from io import BytesIO
        raw=b'observation_date,DGS10\n2026-10-22,invalid\n'
        self.book.capture('us10y',[['2026-10-22','4.96']],mode='manual_transcription')
        with patch('pfa.markets.urlopen',return_value=BytesIO(raw)):
            self.assertIsNone(self.book.refresh_metric('us10y'))
        entry=self.book.entry('us10y')
        self.assertEqual(entry['value'],'4.96')
        failure=entry['last_attempt']
        self.assertIn('数值格式',failure['error'])
        self.assertEqual((self.root/failure['response']['local_path']).read_bytes(),raw)

    def test_fred_csv_blank_is_missing_not_a_source_outage(self):
        from io import BytesIO
        raw=b'observation_date,DGS10\n2026-10-20,5.12\n2026-10-21,\n2026-10-22,4.96\n'
        with patch('pfa.markets.urlopen',return_value=BytesIO(raw)):
            self.assertIsNotNone(self.book.refresh_metric('us10y'))
        entry=self.book.entry('us10y')
        self.assertEqual(entry['value'],'4.96')
        self.assertIsNone(entry['history'][1][1])
        self.assertIsNone(entry['change'])
        self.assertEqual(entry['last_attempt']['status'],'succeeded')
