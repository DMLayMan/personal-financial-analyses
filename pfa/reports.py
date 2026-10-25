"""Evidence-led research updates and immutable report snapshots.

Observed changes, causal interpretation and investment valuation are separate.
No broker target, generic parameter or fresh headline becomes an underwritten view.
"""
from datetime import date
from decimal import Decimal
from .assurance import ACTUAL_LABELS, temporal_actual, comparable_period
from .store import digest,now
from .research import Conflict

DOMAIN_NAMES={'company':'公司证据、模型或结论变化','methods':'采用的方法版本变化',
              'market':'市场观察、日期或时效状态变化','events':'研究事件变化','industry':'行业手册变化'}
METRICS={'revenue':'营业收入','net_income':'报告归属净利润','operating_cash_flow':'经营现金流',
         'net_interest_income':'净利息收入'}


def amount(value,unit):
    number=Decimal(str(value))
    return f'{number/Decimal("100000000"):,.2f} 亿 {unit}' if abs(number)>=Decimal('100000000') else f'{number:,.2f} {unit}'


def comparable_observations(facts):
    observations=[]
    for metric,label in METRICS.items():
        rows=[f for f in facts if f['metric']==metric and f.get('period_start')]
        pairs=[(a,b) for a in rows for b in rows if comparable_period(a,b) and Decimal(b['value'])>0]
        if not pairs:continue
        latest=max(a['period_end'] for a,b in pairs)
        seen=set()
        for current,prior in sorted(pairs,key=lambda pair:pair[0]['period_start']):
            identity=(current['period_start'],current['period_end'],current['basis'],current['scope'])
            if current['period_end']!=latest or identity in seen:continue
            seen.add(identity)
            change=Decimal(current['value'])/Decimal(prior['value'])-1
            observations.append(dict(metric=metric,label=label,current=current,prior=prior,
                change=str(change),difference=str(Decimal(current['value'])-Decimal(prior['value'])),
                formula='(同口径本期 / 上年同期 − 1) × 100%；没有将中期年度化',
                fact_ids=[current['id'],prior['id']]))
    return observations


def findings(view,industry):
    actual=[f for f in view['quality']['usable'] if f.get('evidence_label') in ACTUAL_LABELS and temporal_actual(f)]
    observations=comparable_observations(actual)
    items=[]
    by_id={f['id']:f for f in view['quality']['usable']}
    for monitor in view['quality']['monitors']:
        refs=[by_id[i] for i in monitor['fact_ids'] if i in by_id]
        unit=refs[0]['unit'] if refs else ''
        if monitor.get('current') is not None and monitor.get('prior') is not None:
            observation=f"单季CFO {amount(monitor['current'],unit)}，上年同期 {amount(monitor['prior'],unit)}，同比 {Decimal(monitor['change'])*100:+.2f}%。"
            formula='单季 = 同年9M累计 − H1累计；同比 = 本期单季 / 上年同期单季 − 1'
        else:
            observation='；'.join(f"{f['label']}：{amount(f['value'],f['unit'])}（{f['period_start']}至{f['period_end']}）" for f in refs)
            formula='同期间不同现金定义并列；剔除项目不能撤销已经发生的现金付款。'
        items.append(dict(kind='monitor',title=monitor['title'],signal='requires_explanation',
            observation=observation,formula=formula,trigger_rule=monitor.get('rule'),fact_ids=monitor['fact_ids'],
            transmission=monitor['mechanism'],financial_effect='现金观察/口径需要解释，并核对营运资本和资本承诺。',
            valuation_effect='尚未把原因、持续性或净暴露写入预测；保留估值限制。',
            counter=industry['opposition'],next_evidence=monitor['next_source'],methods=['method:owner_earnings','method:cfa']))
    # Keep more than one same-end period when both YTD and single quarter are comparable.
    for obs in observations:
        c,p=obs['current'],obs['prior'];percent=(Decimal(obs['change'])*100).quantize(Decimal('.01'))
        items.append(dict(kind='reported_comparison',title=f"{obs['label']}同比{percent:+}%",signal='reported_change',
            observation=f"{c['period_start']}至{c['period_end']}：{amount(c['value'],c['unit'])}；上年同期 {amount(p['value'],p['unit'])}。{c['basis']} / {c['scope']}",
            fact_ids=obs['fact_ids'],formula=obs['formula'],change=obs['change'],
            transmission=industry['bridge'],financial_effect=f"报告值相差 {amount(obs['difference'],c['unit'])}；归因和正常化仍需核验。",
            valuation_effect='尚未证明变化可持续，也未建立个股经营预测及资本桥；不据此调整目标价。',
            counter=industry['opposition'],next_evidence=industry['verification'],methods=['method:cfa','method:growth']))
    return items,observations


class ReportEngine:
    def __init__(self,research,knowledge,information):
        self.research,self.store,self.knowledge,self.information=research,research.store,knowledge,information

    def cursor(self):
        with self.store.tx() as db:return db.execute('SELECT COALESCE(MAX(sequence),0) FROM audit').fetchone()[0]

    def attach(self,base,view):
        issuer=base['company']['id'];industry=base['industry']
        methods=self.knowledge.applicable(issuer,industry['id'])
        items,observations=findings(view,industry)
        information=self.information.related(issuer)
        public_cutoff=max((d.get('published_at') or '' for d in view['documents']),default='')[:10]
        unread=[i for i in information if i['published_at'][:10]>public_cutoff and i['verification']=='unreviewed_metadata']
        connected=any(s['issuer']==issuer and s['last_attempt'] and s['last_attempt']['status']=='succeeded'
                      and s['archive_integrity']=='matched' for s in self.information.read()['sources'])
        model=base['model']
        checks=[dict(key='financial_facts',name='适用历史事实与原件',passed=bool(base['financials']) and not view['quality']['conflicts']),
            dict(key='industry_forecast',name='有证据承保的经营、资本与融资预测',passed=bool(model and not model.get('stale') and model.get('support_assessment')=='industry_underwritten')),
            dict(key='security_price',name='证券身份、当前价格/股数/FX及共同截止点',passed=False),
            dict(key='expectations',name='价格隐含预期及同口径共识/同业比较',passed=False),
            dict(key='counter_review',name='最强反方的专业语义审议',passed=False),
            dict(key='new_disclosures',name='公司新披露覆盖及正文回看',passed=connected and not unread)]
        # These gates describe today's actual capability; a saved snapshot cannot bypass them.
        gate=dict(investment_ready=False,checks=checks,missing=[c['name'] for c in checks if not c['passed']],
            scope='证据研究更新与历史算术；不是已承保的现价投资评级。')
        dependencies=dict(company=dict(revision=view['revision'],model_id=model['id'] if model else None,
            model_stale=bool(model and model.get('stale')),review_id=base['review']['id'] if base['review'] else None,
            conclusion_id=base['conclusion']['id'] if base['conclusion'] else None),
            methods={m['entry_id']:dict(version=m['version'],content=digest({k:m[k] for k in ('content','source_url','falsifier','applies_to','status')})) for m in methods},
            market={m['id']:dict(date=m['date'],value=m['value'],previous_date=m['previous_date'],previous=m['previous'],
                change=m['change'],state=m['state'],stale=m['stale'],
                source_status=(m.get('last_attempt') or {}).get('status')) for m in base['market_context']},
            events=dict(recorded=[e['id'] for e in view['events']],pending_disclosures=[i['id'] for i in unread]),
            industry=digest(industry))
        with self.store.tx() as db:history=self.store.list(db,'research_report',issuer)
        last=history[-1] if history else None
        changed=[key for key in dependencies if last and dependencies[key]!=last['dependencies'].get(key)]
        signal='mixed_or_cash_warning' if view['quality']['monitors'] else 'reported_observations_only' if observations else 'insufficient_evidence'
        base.update(findings=items,financial_observations=observations,methods_applied=methods,
            evidence_map={f['id']:f for f in view['quality']['usable'] if f['id'] in
                ({ident for item in items for ident in item['fact_ids']} | {f['id'] for f in base['financials']})},
            information=information,pending_disclosures=unread,events=view['events'],
            report_summary=dict(business_signal=signal,business_label={
                'mixed_or_cash_warning':'经营与现金信号需合并判断','reported_observations_only':'已有可比观察，持续性待证',
                'insufficient_evidence':'经营方向证据不足'}[signal],
                cash_label='存在待核查的现金/口径信号' if view['quality']['monitors'] else '完整现金与资本桥仍待补齐',
                pricing_label='暂不评定现价吸引力',fact_cutoff=public_cutoff,
                input_note='判断链使用下方事实ID和采用方法；市场变量目前为条件背景，尚无净暴露驱动的自动盈利重算。'),
            valuation_gate=gate,investment_output=dict(rating='not_rated',target_price=None,
                reason='缺口保留，不搬用机构评级或通用参数生成目标价。'),
            dependencies=dependencies,dependency_digest=digest(dependencies),
            report_delta=dict(previous_id=last['id'] if last else None,previous_version=last['version'] if last else None,
                changed_domains=changed,reasons=[DOMAIN_NAMES[k] for k in changed],
                status='needs_review' if changed else 'same_inputs' if last else 'not_saved'),
            report_history=[dict(id=r['id'],version=r['version'],created_at=r['created_at'],reason=r['reason'],
                                  dependency_digest=r['dependency_digest']) for r in history],
            report_kind='evidence_update_draft',research_decision_ready=False)
        base['needs_review']=base['needs_review'] or bool(changed) or bool(unread)
        return base

    def save(self,report,data):
        reason=str(data.get('reason','')).strip()
        if len(reason)<12:raise ValueError('请说明本轮报告的变化、判断边界及保存原因，至少12字')
        if data.get('dependency_digest')!=report['dependency_digest']:raise Conflict('报告依赖已变化，请刷新并重新检查后保存')
        actor=data.get('actor','local_researcher')
        if actor not in ('local_researcher','implementation_acceptance'):raise ValueError('报告保存用途无效')
        with self.store.tx() as db:
            cursor=db.execute('SELECT COALESCE(MAX(sequence),0) FROM audit').fetchone()[0]
            if cursor!=report['dependency_cursor']:raise Conflict('保存时资料发生更新，请重新读取报告；旧版保留')
            issuer=report['company']['id'];prior=self.store.list(db,'research_report',issuer)
            payload=dict(version=len(prior)+1,reason=reason,saved_by=actor,review_status='not_independently_reviewed',dependencies=report['dependencies'],
                dependency_digest=report['dependency_digest'],scope='evidence_update_draft',
                report={k:v for k,v in report.items() if k!='report_history'},research_decision_ready=False,
                source_ids=dict(facts=sorted({f for i in report['findings'] for f in i['fact_ids']}),
                                methods=[dict(entry_id=m['entry_id'],version=m['version']) for m in report['methods_applied']],
                                markets=[dict(id=m['id'],provenance=m.get('provenance')) for m in report['market_context']]))
            item=self.store.add(db,'research_report',issuer,payload)
            self.store.log(db,'_reports','保存研究报告草案',dict(issuer=issuer,report_id=item['id'],version=payload['version']))
            return dict(id=item['id'],version=item['version'],research_decision_ready=False)
