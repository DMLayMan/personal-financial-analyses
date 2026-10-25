"""Import a consistent local workspace into the confirmed owner-private Site.

Remote service credential is read once from stdin; never printed or persisted.
No new cloud version is overwritten: this importer only accepts version zero.
"""
import argparse,hashlib,json,sqlite3,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pfa.store import Store,now

def export(destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    path=Store(ROOT/'data/pfa.sqlite3').backup(destination/'initial.sqlite3')
    with sqlite3.connect(path) as db:
        changed=0
        for ident,payload in db.execute("SELECT id,payload FROM records WHERE kind='document'").fetchall():
            data=json.loads(payload);old=data.get('local_path','')
            if old.startswith(str(ROOT)+'/data/raw/'):
                data['local_path']=str(Path(old).relative_to(ROOT));db.execute('UPDATE records SET payload=? WHERE id=?',(json.dumps(data,ensure_ascii=False,sort_keys=True),ident));changed+=1
        db.execute("INSERT INTO audit(issuer,action,payload,created_at) VALUES (?,?,?,?)",('_migration','一致性快照迁移至私有云端',json.dumps(dict(relocated_paths=changed,source='本地研究空间一致性快照'),ensure_ascii=False),now()))
        db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('导出数据库未通过完整性检查')
    files=[]
    for directory in ('data/raw','data/market/raw','data/information/raw'):
        for raw in sorted((ROOT/directory).rglob('*')):
            if raw.is_file():files.append(dict(path=str(raw.relative_to(ROOT)),sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),bytes=raw.stat().st_size))
    manifest=dict(database=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),files=files)
    (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest

def transfer(origin,token,manifest):
    # Exact fixed target, no redirects (prevent service credential leakage).
    from urllib.request import build_opener,HTTPRedirectHandler
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):raise ValueError('私有服务导入不跟随重定向')
    opener=build_opener(NoRedirect())
    headers={'X-PFA-Request':'1'}
    if token:headers['OAI-Sites-Authorization']='Bearer '+token
    def call(path,method='GET',body=None):
        with opener.open(Request(origin+'/cloud/admin/'+path,data=body,headers=headers,method=method),timeout=60) as r:return json.load(r)
    head=call('state')
    if head['version']!=0:raise ValueError('云端已有版本，导入器拒绝覆盖。请使用显式版本迁移流程。')
    def put(file):
        raw=ROOT/file['path'];body=raw.read_bytes()
        if hashlib.sha256(body).hexdigest()!=file['sha256']:raise ValueError('导出后原件变化')
        call('blobs/'+file['sha256'],'PUT',body)
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(put,manifest['files']))
    call('blobs/'+manifest['sha256'],'PUT',Path(manifest['database']).read_bytes())
    return call('commit','POST',json.dumps(dict(expectedVersion=0,sha256=manifest['sha256'],files=manifest['files'])).encode())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--origin');p.add_argument('--token-stdin',action='store_true');p.add_argument('--export-only',action='store_true');a=p.parse_args()
    manifest=export(ROOT/'data/hosted-import')
    if a.export_only:print(json.dumps(dict(files=len(manifest['files']),bytes=sum(f['bytes'] for f in manifest['files']),sha256=manifest['sha256'])));sys.exit()
    if not a.origin:raise SystemExit('需要明确origin')
    import getpass
    token=(getpass.getpass('Private service credential (hidden): ') if sys.stdin.isatty() else sys.stdin.readline().strip()) if a.token_stdin else None
    result=transfer(a.origin.rstrip('/'),token,manifest)
    print(json.dumps(dict(saved=result,files=len(manifest['files'])),ensure_ascii=False))
