"""Versioned research references and local adaptations, not validated financial rules."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from .store import uid, digest
from .research import Conflict

ROOT=Path(__file__).resolve().parents[1]
CATEGORIES={'theory':'理论','method':'研究方法','industry':'行业补充','risk':'历史与风险','source':'信息源参考'}


def builtins():
    refs=json.loads((ROOT/'knowledge/platform.json').read_text())['references']
    return [dict(entry_id='method:'+r['id'],record_id='builtin:'+r['id']+':1',version=1,title=r['name'],
        category='risk' if r['id'] in ('svb','modelrisk') else 'source' if r['id']=='terminal' else 'industry' if r['id']=='gics' else 'method',content=r['use'],source_url=r['url'],
        applies_to=['platform'] if r['id'] in ('terminal','gics') else ['industry:banks'] if r['id']=='svb' else ['all'],
        status='adopted',falsifier='超出原文适用范围或与证据冲突时重新审议；原文思想不等于当前公司结论。',
        change_reason='内置公开参考，作为研究提问与复核依据；方法有效性仍需按用途验证。',
        method_validated=False,origin='builtin_reference') for r in refs]


class Knowledge:
    def __init__(self,store):self.store=store

    def read(self):
        grouped={r['entry_id']:[r] for r in builtins()}
        with self.store.tx() as db:records=self.store.list(db,'knowledge_revision')
        for r in records:
            r=dict(r,record_id=r['id']);grouped.setdefault(r['entry_id'],[]).append(r)
        entries=[]
        for ident,history in grouped.items():
            active=None
            for revision in history:
                if revision['status']=='adopted':active=revision
                elif revision['status']=='retired':active=None
            entries.append(dict(entry_id=ident,latest=history[-1],active=active,history=history))
        return dict(entries=entries,categories=CATEGORIES,
            adoption_meaning='纳入本地研究参考，不代表方法已获专业或预测有效性验证。')

    def applicable(self,issuer,industry):
        scopes={'all','issuer:'+issuer,'industry:'+industry}
        return [e['active'] for e in self.read()['entries'] if e['active'] and scopes.intersection(e['active']['applies_to'])]

    def save(self,data):
        ident=data.get('entry_id') or uid('method')
        payload={key:str(data.get(key,'')).strip() for key in
                 ('title','category','content','source_url','status','falsifier','change_reason')}
        if not 3<=len(payload['title'])<=180 or not 12<=len(payload['content'])<=16000:
            raise ValueError('需要明确的方法标题与至少12字的正文')
        if payload['category'] not in CATEGORIES or payload['status'] not in ('draft','adopted','retired'):
            raise ValueError('知识类型或状态无效')
        if len(payload['change_reason'])<12:raise ValueError('请说明本次改变什么、为什么，至少12字')
        url=urlparse(payload['source_url'])
        if payload['status']=='adopted' and (url.scheme!='https' or not url.hostname or len(payload['falsifier'])<12):
            raise ValueError('纳入研究参考需要HTTPS原文及明确的适用/失效条件')
        scopes=data.get('applies_to',['all'])
        if not isinstance(scopes,list) or not scopes or len(scopes)>30 or any(not isinstance(s,str) or not re.fullmatch(r'all|platform|(?:issuer|industry):[a-z0-9_-]+',s) for s in scopes):
            raise ValueError('适用范围应为全局、公司或行业标识')
        payload.update(entry_id=ident,applies_to=scopes,method_validated=False,origin='local_adaptation')
        with self.store.tx() as db:
            records=self.store.list(db,'knowledge_revision',ident)
            original=next((r for r in builtins() if r['entry_id']==ident),None)
            latest=records[-1] if records else original
            expected=data.get('expected_version')
            if latest and (expected is None or int(expected)!=latest['version']):
                raise Conflict('知识已更新，请读取最新版本后再修订；旧版会保留')
            if not latest and expected not in (None,0,'0'):raise Conflict('知识版本不存在')
            payload['version']=(latest['version'] if latest else 0)+1
            payload['content_digest']=digest(payload)
            item=self.store.add(db,'knowledge_revision',ident,payload)
            self.store.log(db,'_knowledge','新增知识版本',dict(entry_id=ident,version=payload['version'],status=payload['status']))
            return item
