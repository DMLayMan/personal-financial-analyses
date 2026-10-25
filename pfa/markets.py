"""Public, delayed market observations. Separate from company financial evidence.

Snapshots and attempts are append-only; a failed fetch cannot advance an
observation date. No automatic investment recommendation or macro attribution.
"""
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .store import now, uid, dump

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT/'knowledge/market-catalog.json').read_text())
METRICS = {m['id']: m for m in CATALOG['entries']}


def clean_points(points, asof=None):
    asof = asof or date.today()
    result = {}
    for day, value in points:
        parsed = date.fromisoformat(day)
        if parsed > asof:
            continue
        if isinstance(value,str):
            value=value.strip()
        if value is None or value in ('.',''):
            value = None
        else:
            value = Decimal(str(value))
            if not value.is_finite():
                raise ValueError('观察值不是有限数字')
            value = str(value)
        if day in result and result[day] != value:
            raise ValueError('同一天存在冲突观察值')
        result[day] = value
    return [[d, result[d]] for d in sorted(result)]


def statistics(points, kind):
    points = clean_points(points)
    day, value = points[-1] if points else (None, None)
    prior_day, prior = points[-2] if len(points) > 1 else (None, None)
    unit = 'bp' if kind in ('percent_rate', 'basis_points') else '点' if kind == 'points' else '%'
    change = None
    if value is not None and prior is not None:
        delta = Decimal(value)-Decimal(prior)
        if kind == 'percent_rate':
            delta *= 100
        elif kind not in ('basis_points', 'points'):
            delta = delta/abs(Decimal(prior))*100 if Decimal(prior) else None
        if delta is not None:
            change = str(delta.quantize(Decimal('.01')))
    return dict(date=day, value=value, previous_date=prior_day, previous=prior,
                change=change, change_unit=unit, history=points,
                observations=sum(p[1] is not None for p in points))


def curve(long_points, short_points):
    left, right = dict(clean_points(long_points)), dict(clean_points(short_points))
    return [[d, str((Decimal(left[d])-Decimal(right[d]))*100)
             if left[d] is not None and right[d] is not None else None]
            for d in sorted(left.keys() & right.keys())]


def parse_yahoo(body, asof=None):
    chart = json.loads(body)['chart']
    if chart.get('error') or not chart.get('result'):
        raise ValueError('行情供应商未返回有效序列')
    data = chart['result'][0]
    meta = data['meta']
    timezone = ZoneInfo(meta['exchangeTimezoneName'])
    closes = data['indicators']['quote'][0].get('close', [])
    times = data.get('timestamp', [])
    if len(times) != len(closes) or not times:
        raise ValueError('时间与收盘观察不匹配')
    points = clean_points([[datetime.fromtimestamp(t, timezone).date().isoformat(),
                            str(v) if v is not None else None] for t, v in zip(times, closes)], asof)
    if not any(p[1] is not None for p in points):
        raise ValueError('没有已发生的有效行情观察')
    return points, {k:meta.get(k) for k in ('symbol','currency','exchangeName',
                    'exchangeTimezoneName','instrumentType','regularMarketTime','dataGranularity')}


class MarketBook:
    def __init__(self, store, root=ROOT, workers=3):
        self.store, self.root, self.workers = store, Path(root), workers

    def capture(self, metric_id, points, mode, raw=None, **metadata):
        metric = METRICS[metric_id]
        if metric['provider'] in ('catalog','derived'):
            raise ValueError('目录及派生指标不能作为外部序列录入')
        points = clean_points(points)
        if not any(p[1] is not None for p in points):
            raise ValueError('序列没有有效观察')
        # Transcription is explicitly different from an automatically retrieved payload.
        raw = raw if raw is not None else dump(dict(points=points, source_url=metric['source_url'],
                                      mode=mode, note=metadata.get('note'))).encode()
        sha = hashlib.sha256(raw).hexdigest()
        relative = Path('data/market/raw')/(sha+'.json')
        path = self.root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(raw)
        provenance = dict(source_url=metric['source_url'], retrieved_at=now(), mode=mode,
                          sha256=sha, local_path=str(relative), **metadata)
        with self.store.tx() as db:
            item = self.store.add(db, 'market_snapshot', metric_id,
                                  dict(points=points, provenance=provenance))
            self.store.add(db, 'market_attempt', metric_id, dict(status='succeeded', snapshot_id=item['id']))
            self.store.log(db, '_market', '保存公开市场快照', dict(metric=metric_id, snapshot_id=item['id']))
        return item

    def failure(self, metric_id, error, raw=None, request_url=None):
        response=None
        if raw is not None:
            sha=hashlib.sha256(raw).hexdigest()
            relative=Path('data/market/raw')/(sha+'.json')
            path=self.root/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            if not path.exists():path.write_bytes(raw)
            response=dict(sha256=sha,local_path=str(relative),request_url=request_url)
        with self.store.tx() as db:
            return self.store.add(db, 'market_attempt', metric_id, dict(status='failed', error=str(error)[:500],response=response))

    def entry(self, metric_id):
        metric = METRICS[metric_id]
        with self.store.tx() as db:
            snapshots = self.store.list(db, 'market_snapshot', metric_id)
            attempts = self.store.list(db, 'market_attempt', metric_id)
        snapshot = snapshots[-1] if snapshots else None
        state, points, provenance = 'missing', [], None
        if snapshot:
            provenance = snapshot['provenance']
            raw = (self.root/provenance['local_path']).resolve()
            allowed = (self.root/'data/market/raw').resolve()
            valid = allowed in raw.parents and raw.is_file() and hashlib.sha256(raw.read_bytes()).hexdigest() == provenance['sha256']
            state = 'snapshot' if valid else 'integrity_failed'
            points = snapshot['points'] if valid else []
        elif metric['provider'] == 'catalog':
            state = 'catalog'
        result = dict(metric, **statistics(points, metric['kind']), state=state,
                      provenance=provenance, last_attempt=attempts[-1] if attempts else None,
                      realtime=False, history_is_point_in_time=False)
        if metric_id == 'curve_10_2':
            left, right = self.entry('us10y'), self.entry('us2y')
            result.update(statistics(curve(left['history'], right['history']), metric['kind']))
            result['state'] = 'derived' if result['value'] is not None else 'missing'
            result['inputs'] = [dict(id=m['id'], date=m['date'], provenance=m['provenance'],
                                    last_attempt=m['last_attempt']) for m in (left,right)]
        result['age_days'] = (date.today()-date.fromisoformat(result['date'])).days if result['date'] else None
        result['stale'] = result['age_days'] is not None and result['age_days'] > metric['stale_after_days']
        threshold = metric.get('review_threshold')
        result['attention'] = dict(triggered=bool(threshold and result['change'] is not None
                                                 and abs(Decimal(result['change'])) >= Decimal(threshold)),
            threshold=threshold, unit=result['change_unit'], limit='研究关注条件，未经校准；不是交易指令或损失概率。')
        return result

    def read(self):
        entries = [self.entry(m['id']) for m in CATALOG['entries']]
        with self.store.tx() as db:
            jobs = [dict(r, payload=json.loads(r['payload'])) for r in db.execute(
                "SELECT * FROM jobs WHERE issuer='_market' ORDER BY created_at DESC LIMIT 5")]
        return dict(version=CATALOG['version'], posture=CATALOG['posture'], groups=CATALOG['groups'],
                    interpretation=CATALOG['interpretation'], entries=entries, jobs=jobs,
                    observed=sum(e['value'] is not None for e in entries),
                    automated_available=sum(e['provider'] in ('yahoo','fred_public') for e in entries),
                    manual_snapshots=sum(e['provenance'] is not None and e['provenance']['mode']=='manual_transcription' for e in entries),
                    continuous_monitoring=False, read_at=now())

    def refresh_metric(self, metric_id):
        metric = METRICS[metric_id]
        raw,url=None,None
        try:
            if metric['provider'] == 'yahoo':
                url = 'https://query1.finance.yahoo.com/v8/finance/chart/'+quote(metric['symbol'],safe='')+'?range=6mo&interval=1d'
                request = Request(url, headers={'User-Agent':'PersonalFinancialAnalyses/0.4 (personal local research)'})
                with urlopen(request, timeout=12) as response:
                    raw = response.read(4_000_001)
                if len(raw)>4_000_000:
                    raise ValueError('行情响应超过上限')
                points, vendor = parse_yahoo(raw)
                expected_type='INDEX' if metric['kind'] in ('index','points') else 'CURRENCY' if metric['kind']=='fx' else 'FUTURE'
                if vendor.get('symbol') != metric['symbol'] or vendor.get('instrumentType') != expected_type:
                    raise ValueError('返回证券标识或品种与目录不符，停用该响应')
                return self.capture(metric_id, points, 'public_vendor_json', raw, request_url=url,
                                    vendor=vendor, note='供应商延迟观察；当日可能为盘中值；非总回报，非历史时点数据。')
            if metric['provider'] == 'fred_public':
                # Try a bounded direct read; no silent vendor substitution for a different series.
                import csv
                import io
                url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+metric['series']
                with urlopen(Request(url,headers={'User-Agent':'PersonalFinancialAnalyses/0.4'}),timeout=8) as response:
                    raw=response.read(4_000_001)
                if len(raw)>4_000_000: raise ValueError('FRED响应超过上限')
                rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
                if len(rows)<2 or len(rows[0])!=2 or rows[0][1]!=metric['series']:
                    raise ValueError('FRED未返回预期序列')
                return self.capture(metric_id,rows[1:][-150:],'fred_csv',raw,request_url=url,
                                    note='FRED当前版本历史，非历史时点初值。')
            return None
        except (OSError, ValueError, KeyError, InvalidOperation, IndexError) as exc:
            reason='来源数值格式不符合定义，旧快照保留；失败响应已留存供核对。' if isinstance(exc,InvalidOperation) else str(exc)
            self.failure(metric_id, reason, raw=raw, request_url=url)
            return None

    def enqueue(self):
        with self.store.tx() as db:
            active=db.execute("SELECT id FROM jobs WHERE issuer='_market' AND status IN ('queued','running')").fetchone()
            if active: return dict(id=active['id'],deduplicated=True)
            ident=uid('markets')
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)',
                       (ident,'_market',dump(dict(type='market_refresh')),'queued',0,None,now(),now()))
            return dict(id=ident)

    def one(self):
        with self.store.tx() as db:
            row=db.execute("SELECT * FROM jobs WHERE issuer='_market' AND status='queued' AND attempts<3 ORDER BY created_at LIMIT 1").fetchone()
            if row is None: return False
            ident=row['id']
            db.execute("UPDATE jobs SET status='running',attempts=attempts+1,updated_at=? WHERE id=?",(now(),ident))
        # Independent public requests run concurrently with conservative limits.
        ids=[m['id'] for m in CATALOG['entries'] if m['provider'] in ('yahoo','fred_public')]
        if self.workers==1:
            results=list(map(self.refresh_metric,ids))
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                results=list(pool.map(self.refresh_metric,ids))
        failed=[key for key,result in zip(ids,results) if result is None]
        with self.store.tx() as db:
            db.execute('UPDATE jobs SET status=?,error=?,updated_at=? WHERE id=?',
                       ('failed' if failed else 'succeeded','部分来源失败：'+', '.join(failed) if failed else None,now(),ident))
        return True
