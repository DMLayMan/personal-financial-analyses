"""Official feed metadata is an unreviewed lead, not automatically a verified fact."""
import json
import tempfile
import unittest
from pathlib import Path
from pfa.information import Information
from pfa.store import Store


class InformationContract(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.info=Information(Store(Path(self.temp.name)/'test.db'),root=Path(self.temp.name))

    def tearDown(self):self.temp.cleanup()

    def test_duplicates_and_future_items_are_controlled(self):
        raw=b'''<rss><channel><item><title>Policy announcement</title><link>https://www.federalreserve.gov/newsevents/pressreleases/test.htm</link><pubDate>Thu, 22 Oct 2026 14:00:00 GMT</pubDate></item><item><title>Future item</title><link>https://www.federalreserve.gov/future.htm</link><pubDate>Thu, 01 Jan 2099 14:00:00 GMT</pubDate></item></channel></rss>'''
        self.info.ingest('fed_press',raw);self.info.ingest('fed_press',raw)
        items=self.info.read()['items']
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['title'],'Policy announcement')

    def test_feed_metadata_is_not_verified_financial_fact(self):
        raw=json.dumps(dict(cik='0000789019',filings=dict(recent=dict(form=['8-K'],filingDate=['2026-10-22'],
            acceptanceDateTime=['2026-10-22T14:00:00Z'],accessionNumber=['0000789019-26-000001'],primaryDocument=['test.htm'])))).encode()
        self.info.ingest('sec_msft',raw)
        item=self.info.read()['items'][0]
        self.assertEqual(item['issuer'],'msft')
        self.assertEqual(item['verification'],'unreviewed_metadata')
        with self.info.store.tx() as db:self.assertFalse(self.info.store.list(db,'fact'))
        self.assertFalse(self.info.read()['delivery']['continuous_realtime'])

    def test_company_source_worker_does_not_consume_information_jobs(self):
        from pfa.research import Research
        from pfa.sources import Jobs
        self.info.enqueue()
        self.assertFalse(Jobs(Research(self.info.store),self.info.root).one())

    def test_wrong_filer_identity_and_external_feed_links_are_rejected(self):
        with self.assertRaises(ValueError):self.info.ingest('sec_msft',b'{"cik":"909832"}')
        raw=b'<rss><channel><item><title>Bad link</title><link>https://untrusted.example/policy</link><pubDate>Thu, 22 Oct 2026 14:00:00 GMT</pubDate></item></channel></rss>'
        self.info.ingest('fed_press',raw)
        self.assertFalse(self.info.read()['items'])

    def test_tampered_information_raw_is_marked_unavailable(self):
        raw=b'<rss><channel><item><title>Policy announcement</title><link>https://www.federalreserve.gov/test.htm</link><pubDate>Thu, 22 Oct 2026 14:00:00 GMT</pubDate></item></channel></rss>'
        batch=self.info.ingest('fed_press',raw)
        (self.info.root/batch['local_path']).write_text('tampered')
        result=self.info.read()
        self.assertEqual(result['items'][0]['verification'],'source_archive_unavailable')
        self.assertEqual(result['sources'][0]['archive_integrity'],'hash_mismatch')

    def test_global_timeline_limit_does_not_hide_company_filings(self):
        raw=json.dumps(dict(cik='0000789019',filings=dict(recent=dict(form=['8-K'],filingDate=['2026-10-22'],
            acceptanceDateTime=['2026-10-22T14:00:00Z'],accessionNumber=['0000789019-26-000001'],primaryDocument=['test.htm'])))).encode()
        self.info.ingest('sec_msft',raw)
        for batch in range(3):
            items=''.join(f'<item><title>Macro {i}</title><link>https://www.federalreserve.gov/test-{i}.htm</link><pubDate>Sat, 24 Oct 2026 14:00:00 GMT</pubDate></item>' for i in range(batch*50,(batch+1)*50))
            self.info.ingest('fed_press',f'<rss><channel>{items}</channel></rss>'.encode())
        self.assertEqual(len(self.info.read()['items']),100)
        self.assertEqual(len(self.info.related('msft')),1)
