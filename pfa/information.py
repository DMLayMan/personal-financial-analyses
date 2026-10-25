"""Small primary-source information adapters with explicit manual-pull delivery."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse,quote
from urllib.request import Request,urlopen
from .store import now,uid,dump,digest

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
    dict(id='fed_press',name='美联储公开新闻RSS',url='https://www.federalreserve.gov/feeds/press_all.xml',
         type='rss',issuer=None,host='www.federalreserve.gov',coverage='美国政策/监管；相关性需逐事件判断'),
    dict(id='sec_msft',name='SEC微软提交记录',url='https://data.sec.gov/submissions/CIK0000789019.json',
         type='sec',issuer='msft',cik='0000789019',host='www.sec.gov',coverage='微软10-K/10-Q/8-K及股东材料元数据'),
    dict(id='sec_cost',name='SEC Costco提交记录',url='https://data.sec.gov/submissions/CIK0000909832.json',
         type='sec',issuer='cost',cik='0000909832',host='www.sec.gov',coverage='Costco 10-K/10-Q/8-K及股东材料元数据'),
]
CATALOG={s['id']:s for s in SOURCES}


def timestamp(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:result=parsedate_to_datetime(value)
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result


def parse_items(source,raw):
    result=[]
    if source['type']=='rss':
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('不接受带实体定义的RSS')
        root=ET.fromstring(raw)
        if root.tag!='rss':raise ValueError('来源未返回RSS频道')
        for item in root.findall('./channel/item')[:50]:
            result.append(dict(title=item.findtext('title',''),url=item.findtext('link',''),
                               published_at=item.findtext('pubDate',''),category='policy_release',issuer=None))
    else:
        data=json.loads(raw)
        if int(data.get('cik','-1'))!=int(source['cik']):raise ValueError('提交记录发行人CIK与目录不符')
        recent=data.get('filings',{}).get('recent',{})
        for index,form in enumerate(recent.get('form',[])):
            if form not in ('10-K','10-K/A','10-Q','10-Q/A','8-K','8-K/A','DEF 14A'):continue
            accession=recent['accessionNumber'][index];document=recent['primaryDocument'][index]
            if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession) or '..' in document:raise ValueError('提交记录路径无效')
            public=(recent.get('acceptanceDateTime') or recent['filingDate'])[index]
            result.append(dict(title=form+' · '+recent['filingDate'][index]+' · '+document,
                url=f"https://www.sec.gov/Archives/edgar/data/{int(source['cik'])}/{accession.replace('-','')}/{quote(document,safe='/._-')}",
                published_at=public,category=form,issuer=source['issuer']))
            if len(result)>=25:break
    valid=[]
    for item in result:
        try:published=timestamp(item['published_at'])
        except (ValueError,TypeError,OverflowError):continue
        url=urlparse(item['url'])
        if published>datetime.now(timezone.utc) or url.scheme!='https' or url.hostname!=source['host']:continue
        item.update(title=re.sub(r'<[^>]*>','',item['title'])[:300],published_at=published.isoformat(),
                    verification='unreviewed_metadata',source_id=source['id'])
        valid.append(item)
    return valid


class Information:
    def __init__(self,store,root=ROOT):self.store,self.root=store,Path(root)

    def archive_integrity(self,attempt):
        if not attempt:return 'missing'
        try:
            path=(self.root/attempt['local_path']).resolve()
            if (self.root/'data/information/raw').resolve() not in path.parents:return 'outside_source_directory'
            return 'matched' if hashlib.sha256(path.read_bytes()).hexdigest()==attempt['sha256'] else 'hash_mismatch'
        except (KeyError,OSError):return 'missing'

    def ingest(self,source_id,raw):
        source=CATALOG[source_id];items=parse_items(source,raw)
        sha=hashlib.sha256(raw).hexdigest();relative=Path('data/information/raw')/(sha+'.json')
        path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_bytes(raw)
        with self.store.tx() as db:
            batch=self.store.add(db,'information_attempt',source_id,dict(status='succeeded',retrieved_at=now(),
                source_url=source['url'],sha256=sha,local_path=str(relative),received_items=len(items)))
            for item in items:
                ident='information_'+digest(item)[:24]
                if db.execute('SELECT 1 FROM records WHERE id=?',(ident,)).fetchone():continue
                self.store.add(db,'information_item',item.get('issuer') or '_macro',dict(item,first_seen_at=now(),batch_id=batch['id']),ident)
            self.store.log(db,'_information','取得公开信息元数据',dict(source=source_id,count=len(items)))
        return batch

    def refresh(self,source_id):
        try:
            with urlopen(Request(CATALOG[source_id]['url'],headers={'User-Agent':'PersonalFinancialAnalyses/0.5 (personal local research)'}),timeout=12) as response:
                raw=response.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError('公开信息响应超过上限')
            return self.ingest(source_id,raw)
        except (OSError,ValueError,KeyError,TypeError,ET.ParseError) as exc:
            with self.store.tx() as db:
                self.store.add(db,'information_attempt',source_id,dict(status='failed',error=str(exc)[:500],retrieved_at=now()))
                self.store.log(db,'_information','公开信息读取失败',dict(source=source_id,error=str(exc)[:500]))
            return None

    def read(self,limit=100):
        with self.store.tx() as db:
            items=self.store.list(db,'information_item')
            all_attempts=self.store.list(db,'information_attempt')
            archives={a['id']:self.archive_integrity(a) for a in all_attempts if a['status']=='succeeded'}
            sources=[]
            for source in SOURCES:
                attempts=[a for a in all_attempts if a['issuer']==source['id']]
                successes=[a for a in attempts if a['status']=='succeeded']
                sources.append(dict(source,last_attempt=attempts[-1] if attempts else None,update_mode='manual_pull',
                                    archive_integrity=self.archive_integrity(successes[-1] if successes else None),
                                    verified_body=False,continuous_validated=False))
            jobs=[dict(r,payload=json.loads(r['payload'])) for r in db.execute("SELECT * FROM jobs WHERE issuer='_information' ORDER BY created_at DESC LIMIT 5")]
        items.sort(key=lambda i:i['published_at'],reverse=True)
        for item in items:
            item['source_integrity']=archives.get(item['batch_id'],'missing')
            if item['source_integrity']!='matched':item['verification']='source_archive_unavailable'
        return dict(items=items if limit is None else items[:limit],sources=sources,jobs=jobs,
            delivery=dict(update_mode='manual_pull',continuous_realtime=False,
                explanation='上游公告可能持续发布；本站当前按需获取，显示公开与取得时间，没有秒级推送或全市场新闻保证。',
                missing='港股/A股公告流、授权新闻/共识、实时行情推送及日历调度尚未接入。'))

    def related(self,issuer):return [i for i in self.read(limit=None)['items'] if i.get('issuer')==issuer][:25]

    def enqueue(self):
        with self.store.tx() as db:
            active=db.execute("SELECT id FROM jobs WHERE issuer='_information' AND status IN ('queued','running')").fetchone()
            if active:return dict(id=active['id'],deduplicated=True)
            ident=uid('information_job');db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)',
                (ident,'_information',dump(dict(type='information_refresh')),'queued',0,None,now(),now()))
            return dict(id=ident)

    def one(self):
        with self.store.tx() as db:
            row=db.execute("SELECT * FROM jobs WHERE issuer='_information' AND status='queued' AND attempts<3 ORDER BY created_at LIMIT 1").fetchone()
            if row is None:return False
            ident=row['id'];db.execute("UPDATE jobs SET status='running',attempts=attempts+1,updated_at=? WHERE id=?",(now(),ident))
        # Only three selected sources; bounded sequential requests respect public endpoints.
        failed=[s['id'] for s in SOURCES if self.refresh(s['id']) is None]
        with self.store.tx() as db:
            db.execute('UPDATE jobs SET status=?,error=?,updated_at=? WHERE id=?',
                ('failed' if failed else 'succeeded','读取失败：'+','.join(failed) if failed else None,now(),ident))
        return True
