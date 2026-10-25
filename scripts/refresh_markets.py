"""Explicit local public snapshot refresh or labelled manual transcription import."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pfa.markets import MarketBook, METRICS
from pfa.store import Store


def main():
    parser=argparse.ArgumentParser(description='更新公开市场快照；没有启用定时任务')
    parser.add_argument('--db',default=str(ROOT/'data/pfa.sqlite3'))
    parser.add_argument('--import-transcription',type=Path)
    args=parser.parse_args()
    book=MarketBook(Store(args.db))
    if args.import_transcription:
        capture=json.loads(args.import_transcription.read_text())
        for item in capture['series']:
            if item['source_url']!=METRICS[item['id']]['source_url']:
                raise ValueError('转录来源与目录不一致')
            book.capture(item['id'],item['points'],'manual_transcription',
                         json.dumps(item,ensure_ascii=False).encode(),
                         note=item['note'],source_updated_at=item.get('source_updated_at'))
    else:
        book.enqueue()
        book.one()
    data=book.read()
    print(json.dumps(dict(observed=data['observed'],series=[dict(id=e['id'],date=e['date'],value=e['value'],
          observations=e['observations'],last_attempt=e['last_attempt']['status'] if e['last_attempt'] else None)
          for e in data['entries'] if e['provider']!='catalog']),ensure_ascii=False,indent=2))
    return 0 if args.import_transcription or not data['jobs'] or data['jobs'][0]['status']=='succeeded' else 1


if __name__=='__main__':sys.exit(main())
