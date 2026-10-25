"""Methods, knowledge, source coverage and industry research above company cases."""
import hashlib
import json
from pathlib import Path

from .store import now, digest
from .assurance import ACTUAL_LABELS, temporal_actual

ROOT=Path(__file__).resolve().parents[1]
FOUNDATION=json.loads((ROOT/'knowledge/platform.json').read_text())
INDUSTRIES=json.loads((ROOT/'knowledge/industries.json').read_text())
LIBRARY={
    'architecture': ('三层平台方案', 'docs/three-layer-architecture.md'),
    'methodology': ('研究方法与理论', 'docs/research-methodology.md'),
    'review': ('审查结论与问题', 'docs/quality/review-2026-10-25.md'),
    'feature_plan': ('功能与验证计划', 'docs/quality/feature-plan.md'),
    'verification': ('质量评价标准', 'docs/quality/verification-standard.md'),
    'markets': ('市场与信息框架', 'docs/market-framework.md'),
    'industries': ('行业研究与报告合同', 'docs/industry-research.md'),
    'sources': ('数据来源与可得性', 'docs/data-sources.md'),
    'references': ('理论与公开依据', 'docs/references.md'),
    'operations': ('本地运行与部署', 'docs/operations/local-service.md'),
}


class Platform:
    def __init__(self, research, markets):
        self.research, self.markets=research,markets

    def overview(self):
        data=dict(FOUNDATION)
        report_path=ROOT/'quality/latest-functional.json'
        if report_path.is_file():
            report=json.loads(report_path.read_text())
            manifest=report.get('source_manifest',{})
            current=bool(manifest) and all((ROOT/path).is_file() and
                hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha for path,sha in manifest.items())
            data['verification']=dict(run_at=report.get('run_at'),functional_passed=report.get('functional_passed'),
                                      evidence_current=current,research_decision_ready=False,
                                      tests_run=report.get('tests_run'),scope='功能与控制验证；研究充分性和预测能力未获验证')
        else:
            data['verification']=dict(functional_passed=None,evidence_current=False,research_decision_ready=False)
        data['library']=[dict(id=key,title=value[0],path=value[1]) for key,value in LIBRARY.items()]
        data['features']=json.loads((ROOT/'quality/features.json').read_text())['features']
        data['read_at']=now()
        return data

    @staticmethod
    def library(ident):
        if ident not in LIBRARY: raise ValueError('文档不存在或不在可读目录')
        title,path=LIBRARY[ident]
        return dict(id=ident,title=title,path=path,text=(ROOT/path).read_text())

    @staticmethod
    def industries():
        return INDUSTRIES

    def report(self, issuer):
        v=self.research.view(issuer)
        industry=next(i for i in INDUSTRIES['industries'] if issuer in i['companies'])
        model=v['models'][-1] if v['models'] else None
        conclusion=v['conclusions'][-1] if v['conclusions'] else None
        review=v['reviews'][-1] if v['reviews'] else None
        financials={}
        for f in v['quality']['usable']:
            if f.get('evidence_label') not in ACTUAL_LABELS or not temporal_actual(f):
                continue
            key=(f['metric'],f['basis'],f['scope'],f['unit'])
            if key not in financials or f['period_end']>financials[key]['period_end']:
                financials[key]=f
        market_entries=[self.markets.entry(key) for key in industry['macro']]
        channels=[dict(metric=key,mechanism=text,observation=next(m for m in market_entries if m['id']==key),
                       posture='条件传导；净暴露、套保、时滞与预期未定前，不计算公司盈利影响或评级。')
                  for key,text in industry['channels']]
        context=digest(dict(industry=industry,market=[dict(id=m['id'],date=m['date'],value=m['value'],
                       snapshot=m.get('provenance')) for m in market_entries]))
        return dict(company=v['company'],industry=industry,sections=INDUSTRIES['report_sections'],
                    hypothesis=v['hypothesis'],financials=list(financials.values()),
                    evidence=dict(documents=len(v['documents']),verified=v['quality']['verified'],
                                  candidates=v['quality']['candidates'],conflicts=len(v['quality']['conflicts'])),
                    monitors=v['quality']['monitors'],gaps=v['quality']['gaps'],macro_channels=channels,
                    market_context=market_entries,model=model,review=review,conclusion=conclusion,
                    needs_review=not conclusion or any(x and x.get('stale') for x in (model,review,conclusion)),
                    research_decision_ready=False,autonomous_research=False,
                    confidence=dict(facts='按原文、单位、期间与冲突逐项核对；局部核验不代表覆盖完整。',
                                    mechanism='行业传导模板及待证假设，尚未完成经营预测桥和独立语义审查。',
                                    valuation='当前模型为示例，缺证券价格/共识时点和个股参数承保。',
                                    probability=None,calibration='未校准，不输出获利概率或装饰性总分。'),
                    workflow_application=[dict(step='资料与核验',result=f"{len(v['documents'])}份原文，{v['quality']['verified']}项局部核验；按口径分别保留",tab='evidence'),
                        dict(step='主动补证',result=f"{len(v['quality']['gaps'])}个已登记缺口；下一经营验证：{industry['verification']}",tab='gaps'),
                        dict(step='盈利与估值',result='已存示例模型；行业经营到全年预测桥尚未完成' if model else '尚未运行示例模型；需要经营及资本驱动依据',tab='models'),
                        dict(step='反方与报告',result='有分步复核记录，尚未经独立专业语义审查' if review else '尚无复核记录；先检查最强替代解释与推翻条件',tab='review')],
                    revision=v['revision'],context_digest=context,generated_at=now(),
                    context_note='行业与市场背景按本次读取组合展示；不会自动重算旧模型或改写已发布结论。报告是研究草案，旧结论版本和依赖状态保留。')
