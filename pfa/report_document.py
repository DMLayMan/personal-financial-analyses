"""A portable human-readable research update, rendered entirely from report records."""
from html import escape
from urllib.parse import urlparse
from decimal import Decimal
import base64
import hashlib
import re


def esc(value):return escape(str(value if value is not None else ''))


def link(url,label):
    parsed=urlparse(url or '')
    return f'<a href="{esc(url)}">{esc(label)}</a>' if parsed.scheme=='https' and parsed.hostname else esc(label)


def content_policy(html):
    # Only this generated style is allowed; report data cannot execute script/style.
    style=re.search(r'<style>(.*?)</style>',html,re.S).group(1)
    sha=base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
    return f"default-src 'none'; style-src 'sha256-{sha}'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


def document(report):
    r=report;summary=r['report_summary'];evidence=r['evidence_map']
    style='''body{font:15px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;color:#24332f;margin:35px auto;max-width:980px;padding:0 24px}h1{font-size:30px}h2{border-bottom:1px solid #d9e1dc;padding-bottom:9px;margin-top:35px}h3{font-size:17px}small,.muted{color:#69766e}.notice{padding:18px;border-left:4px solid #436c59;background:#eff4ef}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #ddd}a{color:#285e4d;overflow-wrap:anywhere}.columns{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.finding{border:1px solid #dce1d9;padding:18px;margin:15px 0}.num{font-variant-numeric:tabular-nums}li{margin-bottom:9px}@media(max-width:640px){.columns{grid-template-columns:1fr}body{padding:0 14px}table{display:block;overflow:auto}}@media print{body{font-size:11px;margin:0;max-width:none}a{color:inherit}h2,.finding{break-inside:avoid}.notice{background:none}}'''
    parts=[f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(r["company"]["name"])} · 研究更新</title><style>{style}</style><body>',
        '<small>PERSONAL FINANCIAL ANALYSES / EVIDENCE RESEARCH UPDATE</small>',
        f'<h1>{esc(r["company"]["name"])} · 研究更新</h1><p>{esc(r["industry"]["name"])} / 报告币种 {esc(r["company"]["currency"])}</p>',
        f'<p class="muted">生成 {esc(r["generated_at"])} · 公司原文公开截止 {esc(summary["fact_cutoff"] or "未确认")} · 研究依赖 {esc(r["dependency_digest"][:20])}</p>',
        '<div class="notice"><strong>研究草案 · 未评级 · 目标价未形成</strong><p>本稿用于证据观察、解释与下一验证。个股经营预测、当前证券定价及独立反方审议尚不完备；保存版本不改变用途。</p></div>',
        '<h2>研究摘要</h2>',f'<p>{esc(r["hypothesis"]["question"])}</p>',
        f'<div class="columns"><div><h3>经营观察</h3>{esc(summary["business_label"])}</div><div><h3>现金与资本</h3>{esc(summary["cash_label"])}</div><div><h3>证券经济性</h3>{esc(summary["pricing_label"])}</div></div>',
        f'<p>{esc(summary["input_note"])}</p><h2>本轮变化</h2><p>{esc("；".join(r["report_delta"]["reasons"]) or "暂无已存版本的实质输入差异；首次草案需建立快照。")}</p>',
        '<h2>关键观察与判断链</h2>']
    for item in r['findings']:
        cites='；'.join(link(evidence[f]['source']['url'],evidence[f]['label']+' / '+evidence[f]['period_end']+' / '+evidence[f]['locator']) for f in item['fact_ids'] if f in evidence)
        parts.append(f'<article class="finding"><h3>{esc(item["title"])}</h3><p>{esc(item["observation"])}</p><p class="muted">{esc(item.get("formula",""))}</p><p><b>经营与财务：</b>{esc(item["transmission"])} {esc(item["financial_effect"])}</p><p><b>估值边界：</b>{esc(item["valuation_effect"])}</p><p><b>反方：</b>{esc(item["counter"])}</p><p><b>下一证据：</b>{esc(item["next_evidence"])}</p><small>原文：{cites}</small></article>')
    parts.extend(['<h2>市场背景与传导</h2><table><tr><th>指标 / 观察日</th><th>值 / 单位</th><th>经营通道及约束</th></tr>'])
    for ch in r['macro_channels']:
        m=ch['observation'];parts.append(f'<tr><td>{link(m["source_url"],m["name"])}<br>{esc(m["date"] or "未接入")}</td><td>{esc(m["value"] or "缺失")} {esc(m["unit"])}</td><td>{esc(ch["mechanism"])}<br>{esc(ch["posture"])}</td></tr>')
    parts.extend(['</table><h2>事件与较新披露</h2>','<p>取到标题和提交元数据不代表已读正文或已核验财务；关联事件仍须进入事实和模型复核。</p>'])
    for item in r['pending_disclosures']:
        parts.append(f'<p>{esc(item["published_at"])} · {link(item["url"],item["title"])}</p>')
    if not r['pending_disclosures']:parts.append('<p>当前接入范围内未提示更晚公司披露；港A流和完整新闻覆盖尚未接入。</p>')
    for event in r['events']:
        parts.append(f'<p><strong>{esc(event["title"])}</strong> · {link(event["source_url"],"事件原文")}<br>{esc(event["mechanism"])}<br>未知：{esc(event["unknown"])}</p>')
    parts.extend(['<h2>预测、估值与预期差门槛</h2>','<p>当前评级：未评级；目标价：未形成。已有通用情景仅为示例，未升级为个股公允价值。</p><ul>'])
    for check in r['valuation_gate']['checks']:
        parts.append(f'<li>{"本轮局部满足" if check["passed"] else "待完成"}：{esc(check["name"])}</li>')
    parts.extend(['</ul><h2>本稿引用的方法与版本</h2>'])
    for method in r['methods_applied']:
        parts.append(f'<p>{link(method["source_url"],method["title"])} · v{method["version"]}<br>{esc(method["content"])}<br><small>边界：{esc(method["falsifier"])}</small></p>')
    parts.extend(['<h2>优先补证与反证</h2>',f'<p>{esc(r["industry"]["opposition"])}</p>',f'<p>{esc(r["industry"]["verification"])}</p><ul>'])
    for gap in r['gaps']:parts.append(f'<li><strong>{esc(gap["title"])}</strong>：{esc(gap["why"])} 下一来源：{esc(gap["next_source"])}</li>')
    parts.extend(['</ul><h2>量化观察的原文输入</h2><table><tr><th>指标 / 期间</th><th>原始精度值 / 单位</th><th>口径 / 定位</th></tr>'])
    for fact in evidence.values():
        parts.append(f'<tr><td>{esc(fact["label"])}<br>{esc(fact.get("period_start") or "时点")} / {esc(fact["period_end"])}</td><td class="num">{esc(fact["value"])} {esc(fact["unit"])}</td><td>{esc(fact["basis"])} / {esc(fact["scope"])}<br>{link(fact["source"]["url"],fact["locator"])}</td></tr>')
    parts.extend(['</table><p class="muted">本报告引用原文与已存研究台账。事实、解释、预测和动作分别评价；未知与失败版本保留。未作前瞻成功率或机构背书承诺。</p></body></html>'])
    return ''.join(parts)
