"""Verify the exact private deployment without putting credentials in artifacts."""
import argparse,getpass,hashlib,json,sqlite3,sys,tempfile
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pfa.research import Research
from pfa.store import Store
from pfa.platform import Platform
from pfa.markets import MarketBook
from pfa.report_document import document
p=argparse.ArgumentParser();p.add_argument('--origin',required=True);a=p.parse_args();origin=a.origin.rstrip('/')
token=getpass.getpass('Private service credential (hidden): ') if sys.stdin.isatty() else sys.stdin.readline().strip()
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('Do not send service credentials to redirect targets')
opener=build_opener(NoRedirect());checks=[]
def read(path,authenticated=True):
 headers={'OAI-Sites-Authorization':'Bearer '+token} if authenticated else {}
 with opener.open(Request(origin+path,headers=headers),timeout=40) as r:return r.read()
try:
 anonymous=read('/kernel.json',False)
 try:anonymous=json.loads(anonymous)
 except ValueError:anonymous={}
 assert 'files' not in anonymous,'Anonymous source disclosure'
except (HTTPError,ValueError):pass
checks.append(dict(check='anonymous source/data protected by Sites gate',passed=True))
html=read('/').decode();assert 'Personal Financial Analyses' in html and '/bridge.js' in html
checks.append(dict(check='deployed terminal shell',passed=True))
bundle=json.loads(read('/kernel.json'))
for name in ('pfa/research.py','pfa/models.py','pfa/reports.py','pfa/cloud_bridge.py','knowledge/industries.json'):
 assert bundle['files'][name]==(ROOT/name).read_text(),name+' differs from reviewed source'
checks.append(dict(check='deployed financial source matches reviewed local source',passed=True))
state=json.loads(read('/cloud/admin/state'));assert state['version']>0
raw=read('/cloud/admin/blobs/'+state['sha256']);assert hashlib.sha256(raw).hexdigest()==state['sha256']
checks.append(dict(check='cloud database digest',passed=True))
for folder in ('data/raw/','data/market/raw/','data/information/raw/'):
 f=next(f for f in state['files'] if f['path'].startswith(folder));b=read('/cloud/admin/blobs/'+f['sha256']);assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256']
 checks.append(dict(check='sample stored bytes: '+folder,passed=True))
with tempfile.TemporaryDirectory() as directory:
 db=Path(directory)/'cloud.sqlite3';db.write_bytes(raw)
 with sqlite3.connect(db) as sql:assert sql.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 r=Research(Store(db));platform=Platform(r,MarketBook(r.store))
 reports=[]
 for issuer in ('msft','cost','tencent','byd','catl','cmb'):
  report=platform.report(issuer);assert report['findings'] and not report['valuation_gate']['investment_ready'] and report['investment_output']['target_price'] is None
  if issuer=='catl':assert any('14.09' in f['observation'] for f in report['findings'])
  if issuer=='cmb':assert any('普通股股东净利润' in f['title'] for f in report['findings'])
  out=ROOT/'artifacts/v06/cloud-reports'/f'{issuer}.html';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(document(report))
  reports.append(dict(issuer=issuer,findings=len(report['findings']),financial_inputs=len(report['financials']),not_rated=True))
 checks.append(dict(check='six-company reports from actual remote database (local reviewed interpreter)',passed=True))
result=dict(origin=origin,cloud_version=state['version'],stored_files=len(state['files']),checks=checks,reports=reports,
 browser_login='blocked_by_external_auth_security_check',research_decision_ready=False,
 scope='remote private gate, source parity, persisted data and representative byte integrity; report reconstruction uses local Python, not remote browser sign-in')
(ROOT/'quality/evidence/v06-private-deployment-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
