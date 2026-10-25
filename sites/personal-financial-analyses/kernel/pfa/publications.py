"""Serve only reviewed, hash-bound dated publications, never arbitrary paths."""
import base64
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def publication(route):
    catalog=json.loads((ROOT/'knowledge/research-publications.json').read_text())
    row=next((r for r in catalog['publications'] if r['route']==route),None)
    if row is None:return None
    path=(ROOT/row['path']).resolve()
    if not path.is_relative_to((ROOT/'research').resolve()):raise ValueError('报告路径越界')
    body=path.read_bytes()
    if hashlib.sha256(body).hexdigest()!=row['sha256']:raise ValueError('报告版本摘要不一致')
    text=body.decode()
    directives=[]
    for tag in ('style','script'):
        hashes=["'sha256-"+base64.b64encode(hashlib.sha256(x.encode()).digest()).decode()+"'" for x in re.findall(f'<{tag}>(.*?)</{tag}>',text,re.S)]
        directives.append(f'{tag}-src '+(' '.join(hashes) or "'none'"))
    policy="default-src 'none'; "+'; '.join(directives)+"; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    return body,policy
