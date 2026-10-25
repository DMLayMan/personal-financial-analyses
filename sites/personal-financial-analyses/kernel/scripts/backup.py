"""Create a local snapshot; restore into a new directory for recovery checks."""
import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pfa.store import Store, now
from pfa import __version__


def backup(destination, db_path=ROOT/"data/pfa.sqlite3"):
    destination=Path(destination)
    if destination.exists():raise ValueError("备份目标已存在")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        database=Store(db_path).backup(Path(temp)/"pfa.sqlite3")
        manifest={"created_at":now(),"version":__version__,"files":{}}
        files=[(database,"data/pfa.sqlite3")]
        for directory in ('data/raw','data/market/raw','data/information/raw'):
            for path in (ROOT/directory).rglob('*'):
                if path.is_file() and path.suffix.lower() in ('.pdf','.html','.json','.txt'):
                    files.append((path,str(path.relative_to(ROOT))))
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
            for path,name in files:
                manifest['files'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
                archive.write(path,name)
            archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    return manifest


def restore(archive_path,destination):
    destination=Path(destination)
    if destination.exists():raise ValueError("恢复目录必须是新目录，避免覆盖现有研究")
    with zipfile.ZipFile(archive_path) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        for name,expected in manifest['files'].items():
            relative=Path(name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError("备份路径不合法")
            if hashlib.sha256(archive.read(name)).hexdigest()!=expected:
                raise ValueError("备份内容校验失败："+name)
        destination.mkdir(parents=True)
        for name in manifest['files']:
            out=destination/name;out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes(archive.read(name))
    with sqlite3.connect(str(destination/'data/pfa.sqlite3')) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('恢复数据库完整性检查失败')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['backup','restore'])
    parser.add_argument('path')
    parser.add_argument('--destination')
    args=parser.parse_args()
    result=backup(args.path) if args.action=='backup' else restore(args.path,args.destination)
    print(json.dumps({'files':len(result['files']),'action':args.action}))
