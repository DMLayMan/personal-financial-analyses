"""Disposable local cloud acceptance; production mode is read-only by default."""
import json,sys,urllib.request,urllib.error
from concurrent.futures import ThreadPoolExecutor
origin=sys.argv[1]
assert origin.startswith('http://127.0.0.1:'),'Mutation tests only run against the disposable local preview'
checks=[]
def request(path,method='GET',data=None,headers=None):
    req=urllib.request.Request(origin+path,data=json.dumps(data).encode() if data is not None else None,method=method,headers=headers or {})
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors="replace")
        try:return e.code,json.loads(body)
        except ValueError:return e.code,{"error":body[:200]}
status,head=request('/cloud/admin/state');assert status==200 and head['version']>0
status,_=request('/cloud/state');assert status==401;checks.append('ordinary anonymous API rejected')
data=dict(expectedVersion=head['version'],sha256=head['sha256'],files=head['files'])
status,_=request('/cloud/admin/commit','POST',data);assert status==400;checks.append('unmarked mutation rejected')
status,_=request('/cloud/admin/commit','POST',data,{'X-PFA-Request':'1','Origin':'https://other.example'});assert status in (400,403);checks.append('cross-origin mutation rejected')
headers={'X-PFA-Request':'1'}
with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:request('/cloud/admin/commit','POST',data,headers),range(2)))
assert sorted(r[0] for r in results)==[200,409],results;checks.append('two writers: one success, one version conflict')
status,history=request('/cloud/admin/revisions');assert status==200 and len(history)>=2;checks.append('immutable revisions retained')
status,_=request('/cloud/admin/commit','POST',dict(data,files=[dict(path='data/raw/../secret',sha256='a'*64,bytes=1)]),headers);assert status==400;checks.append('path traversal rejected before commit')
status,after=request('/cloud/admin/state');assert after['version']==head['version']+1;checks.append('failed operations did not advance head')
print(json.dumps(dict(checks=checks,passed=True,scope='local cloud persistence and boundary controls, not investment validation'),ensure_ascii=False,indent=2))
