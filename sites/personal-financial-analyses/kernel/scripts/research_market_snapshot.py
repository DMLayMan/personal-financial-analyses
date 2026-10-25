"""A dated, bounded public price reference for the two research reports."""
import hashlib,json,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
from urllib.parse import quote
from datetime import datetime,date,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/research/2026-10-25/market-raw';RAW.mkdir(parents=True,exist_ok=True)
ASOF=date(2026,10,23)
NAMES={'CEG':'Constellation Energy','NEE':'NextEra Energy','ETN':'Eaton','VRT':'Vertiv','NVDA':'NVIDIA','AVGO':'Broadcom','TSM':'TSMC ADR','MU':'Micron','ANET':'Arista Networks','AMD':'AMD','CRWV':'CoreWeave','MSFT':'Microsoft','AMZN':'Amazon','GOOGL':'Alphabet A','META':'Meta','ORCL':'Oracle','PLTR':'Palantir','NOW':'ServiceNow','CRM':'Salesforce','ADBE':'Adobe','SPCX':'SpaceX','1211.HK':'比亚迪H','002594.SZ':'比亚迪A','9988.HK':'阿里巴巴','0700.HK':'腾讯','9888.HK':'百度','2513.HK':'智谱 / Z.AI','0100.HK':'MiniMax','0981.HK':'中芯国际H','300308.SZ':'中际旭创','300502.SZ':'新易盛','002837.SZ':'英维克','600406.SS':'国电南瑞','002028.SZ':'思源电气','300274.SZ':'阳光电源','601138.SS':'工业富联','688256.SS':'寒武纪','688041.SS':'海光信息','688111.SS':'金山办公','002230.SZ':'科大讯飞'}

def retrieve(symbol):
 url='https://query1.finance.yahoo.com/v8/finance/chart/'+quote(symbol,safe='')+'?range=6mo&interval=1d'
 try:
  with urlopen(Request(url,headers={'User-Agent':'PersonalFinancialAnalyses/0.7 personal research'}),timeout=12) as response:raw=response.read(4000001)
  if not raw or len(raw)>4000000:raise ValueError('empty or oversized payload')
  sha=hashlib.sha256(raw).hexdigest();(RAW/(sha+'.json')).write_bytes(raw)
  payload=json.loads(raw)['chart'];r=payload['result'][0];m=r['meta']
  if m['symbol']!=symbol or m['instrumentType']!='EQUITY':raise ValueError('wrong security identity/type')
  tz=ZoneInfo(m['exchangeTimezoneName']);closes=r['indicators']['quote'][0]['close']
  points=[(datetime.fromtimestamp(t,tz).date(),str(c)) for t,c in zip(r['timestamp'],closes) if c is not None and datetime.fromtimestamp(t,tz).date()<=ASOF]
  day,price=max(points)
  previous=[(d,c) for d,c in points if d<day];prior=previous[-1] if previous else None
  return dict(symbol=symbol,name=NAMES[symbol],provider_name=m.get('longName'),currency=m['currency'],exchange=m.get('exchangeName'),timezone=m['exchangeTimezoneName'],observation_date=day.isoformat(),price=price,prior_date=prior[0].isoformat() if prior else None,prior_price=prior[1] if prior else None,status='observed' if day==ASOF else 'stale',source_url=url,source_page='https://finance.yahoo.com/quote/'+symbol+'/',retrieved_at=datetime.now(timezone.utc).isoformat(),sha256=sha,definition='供应商当前版本日K收盘参考；不是全市场实时成交/买卖价，不保证再分发权')
 except Exception as exc:return dict(symbol=symbol,name=NAMES[symbol],status='failed',error=str(exc),source_url=url)

if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(retrieve,NAMES))
 result=dict(as_of=ASOF.isoformat(),provider='Yahoo public chart',realtime=False,history_point_in_time=False,rows=rows)
 target=ROOT/'research/2026-10-25/market-snapshot.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(observed=sum(r['status']=='observed' for r in rows),failures=[r['symbol'] for r in rows if r['status']!='observed']),ensure_ascii=False))
