"""Browser/Pyodide adapter. The research modules remain the source of truth.

The host persists consistent SQLite snapshots after successful calls. No HTTP
server, socket or browser storage is part of the financial calculation layer.
"""
import base64
import io
import json
from pathlib import Path
from urllib.parse import urlparse,parse_qs,quote
from .store import Store
from .research import Research,Conflict
from .sources import Jobs,document_text
from .markets import MarketBook,CATALOG
from .platform import Platform
from .report_document import document
from .assurance import ROOT,RUNNING_KERNEL
from . import __version__


class CachedResponse(io.BytesIO):
    def __init__(self,entry):
        if entry.get('error'):raise OSError(entry['error'])
        super().__init__(base64.b64decode(entry['body']))
        self.url=entry['url'];self.headers={'Content-Type':entry.get('content_type','application/octet-stream')}


class BrowserBridge:
    def __init__(self,path):
        self.store=Store(path);self.research=Research(self.store)
        self.markets=MarketBook(self.store,ROOT,workers=1)
        self.platform=Platform(self.research,self.markets)
        self.jobs=Jobs(self.research,ROOT);self.cache={}

    def install_network(self):
        # Actual requests are awaited by the Web Worker through an authenticated,
        # bounded same-origin proxy. Python receives only this request's bytes.
        from . import sources,markets,information
        def opened(request,**kwargs):
            url=request if isinstance(request,str) else request.full_url
            if url not in self.cache:raise OSError('本轮未取得此原文响应，请重试；不能借用别的响应')
            return CachedResponse(self.cache[url])
        class Opener:
            def open(self,request,**kwargs):return opened(request,**kwargs)
        sources.build_opener=lambda *args:Opener()
        markets.urlopen=information.urlopen=opened

    def pending_urls(self):
        from .information import SOURCES
        with self.store.tx() as db:
            jobs=[dict(row) for row in db.execute("SELECT issuer,payload FROM jobs WHERE status='queued' AND attempts<3")]
        urls=[]
        for row in jobs:
            if row['issuer']=='_market':
                for m in CATALOG['entries']:
                    if m['provider']=='yahoo':urls.append('https://query1.finance.yahoo.com/v8/finance/chart/'+quote(m['symbol'],safe='')+'?range=6mo&interval=1d')
                    if m['provider']=='fred_public':urls.append('https://fred.stlouisfed.org/graph/fredgraph.csv?id='+m['series'])
            elif row['issuer']=='_information':urls.extend(s['url'] for s in SOURCES)
            else:urls.append(json.loads(row['payload'])['url'])
        return list(dict.fromkeys(urls))

    def run_jobs(self):
        self.install_network()
        try:
            for _ in range(25):
                if not (self.markets.one() or self.platform.information.one() or self.jobs.one()):break
        finally:self.cache.clear()

    def snapshot(self,destination):
        self.store.backup(destination)
        files=[]
        for directory in ('data/raw','data/market/raw','data/information/raw'):
            for path in sorted((ROOT/directory).rglob('*')):
                if path.is_file():
                    import hashlib
                    files.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
        return files

    def request(self,path,method='GET',data=None):
        parts=urlparse(path).path.strip('/').split('/')
        r=self.research;p=self.platform
        try:
            if method=='POST':
                if not isinstance(data,dict):raise ValueError('需要JSON对象')
                if parts==['api','markets','refresh']:result=self.markets.enqueue()
                elif parts==['api','information','refresh']:result=p.information.enqueue()
                elif parts==['api','knowledge']:result=p.knowledge.save(data)
                elif len(parts)==4 and parts[:2]==['api','reports'] and parts[3]=='snapshot':result=p.save_report(parts[2],data)
                elif len(parts)==4 and parts[:2]==['api','companies']:
                    issuer,action=parts[2:]
                    result=self.jobs.enqueue(issuer,data) if action=='fetch' else self.jobs.retry(issuer,data) if action=='retry' else r.command(issuer,action,data)
                else:return dict(status=404,body={'error':'地址不存在'})
                return dict(status=200,body={'result':result})
            if method!='GET':raise ValueError('请求方法不支持')
            if parts==['api','bootstrap']:body=dict(csrf='private-cloud-same-origin',companies=r.dashboard(),version=__version__,ai='同版本Python规则与人工审议；未配置外部模型服务')
            elif parts==['api','healthz']:body=dict(status='ready',version=__version__,kernel_digest=RUNNING_KERNEL,runtime='browser_python',database='readable')
            elif parts==['api','platform']:body=p.overview()
            elif parts==['api','industries']:body=p.industries()
            elif parts==['api','markets']:body=self.markets.read()
            elif parts==['api','knowledge']:body=p.knowledge.read()
            elif parts==['api','information']:body=p.information.read()
            elif len(parts)==3 and parts[:2]==['api','reports']:body=p.report(parts[2])
            elif len(parts)==4 and parts[:2]==['api','reports'] and parts[3]=='document':body=dict(html=document(p.report(parts[2])))
            elif len(parts)==3 and parts[:2]==['api','report-versions']:
                with self.store.tx() as db:snapshot=self.store.get(db,parts[2])
                if snapshot['kind']!='research_report':raise ValueError('研究报告版本不存在')
                body=dict(html=document(snapshot['report']),version=snapshot['version'])
            elif len(parts)==3 and parts[:2]==['api','library']:body=p.library(parts[2])
            elif len(parts)==3 and parts[0]=='api' and parts[1] in ('companies','export'):body=r.view(parts[2])
            elif len(parts)==3 and parts[:2]==['api','documents']:
                with self.store.tx() as db:doc=self.store.get(db,parts[2])
                if doc['kind']!='document':raise ValueError('资料不存在')
                body=document_text(doc,ROOT,int(parse_qs(urlparse(path).query).get('page',['1'])[0]))
            else:return dict(status=404,body={'error':'地址不存在'})
            return dict(status=200,body=body)
        except Conflict as exc:return dict(status=409,body={'error':str(exc)})
        except (ValueError,KeyError,TypeError) as exc:return dict(status=400,body={'error':str(exc)})
