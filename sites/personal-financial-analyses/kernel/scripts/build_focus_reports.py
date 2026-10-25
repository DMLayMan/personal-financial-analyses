"""Render the dated, manually researched reports and deterministic diagnostics.

This renderer does not generate investment ratings or infer source facts. Inputs
are the reviewed public-source register, explicit assumptions and dated prices.
"""
from pathlib import Path
from decimal import Decimal,localcontext
from html import escape
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/2026-10-25'
D=lambda x:Decimal(str(x))
E=lambda x:escape(str(x if x is not None else ''))

def read(path):return json.loads((ROOT/path).read_text())
def fmt(n,places=2):return f'{D(n):,.{places}f}'
def yi(n):return fmt(D(n)/D('1e8'))
def bn(n):return fmt(D(n)/D('1e9'))
def pct(n):return fmt(D(n)*100)+'%'
def paragraph(text):return '<p>'+text+'</p>'
def note(text):return '<aside class="notice">'+text+'</aside>'
def table(headers,rows,caption=''):
 return ('<div class="table-wrap"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>')
def section(ident,title,body):return dict(id=ident,title=title,body=body)
def ref(url,label):return f'<a href="{E(url)}" target="_blank" rel="noopener noreferrer">{E(label)}</a>'
def references(sources):
 return ''.join(f'<li id="source-{E(s["id"])}"><b>{E(s["id"])}</b> {ref(s["url"],s["title"])}<span class="source-meta">公开 {E(s.get("published_at",s.get("published","待确认")))} · {E(s.get("period",s.get("period_covered","")))} · {E(s.get("notes",""))}</span></li>' for s in sources)

def cite(ids,sources):
 lookup={s['id']:s for s in sources};return '<span class="cite">'+''.join(ref(lookup[i]['url'],i) for i in ids if i in lookup)+'</span>'

CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:75px}body{margin:0;color:#23352e;background:#f3f4ee;font:15px/1.85 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft Yahei",sans-serif}.top{padding:18px 4%;display:flex;justify-content:space-between;border-bottom:1px solid #d3dbcf;background:#fff;gap:15px}.brand{letter-spacing:.14em;font-size:12px;font-weight:700}a{color:#23634c;text-decoration:none;overflow-wrap:anywhere}a:hover{text-decoration:underline}.shell{display:grid;grid-template-columns:220px minmax(0,1fr);max-width:1420px;margin:auto}.toc{align-self:start;position:sticky;top:16px;padding:28px 18px;max-height:96vh;overflow:auto}.toc a{display:block;margin:0 0 14px;color:#5a6a61;line-height:1.5;font-size:12px}.toc .n{font:11px ui-monospace,monospace;color:#9aa89d;margin-right:8px}.report{min-width:0;padding:35px 35px 80px}.eyebrow{letter-spacing:.13em;color:#6e8173;font:11px ui-monospace,monospace;text-transform:uppercase}h1{font-size:35px;line-height:1.35;letter-spacing:-.02em;margin:16px 0}h2{font-size:24px;line-height:1.45;margin:0 0 18px}h3{font-size:18px;line-height:1.5;margin:24px 0 10px}.deck{font-size:18px;max-width:850px;color:#4e6457}.meta{color:#758278;font-size:12px}.posture{background:#183b2d;color:#edf5e9;padding:24px;margin:24px 0;border-radius:4px}.posture strong{font-size:20px}.posture p{margin-bottom:0}.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:24px 0}.kpi{background:#fff;border:1px solid #d9e1d4;padding:16px}.kpi label{display:block;font-size:12px;color:#687d6d}.kpi b{font-size:24px;display:block;font-variant-numeric:tabular-nums}.kpi small{font-size:11px;color:#7b897e}.section{background:#fff;border:1px solid #d7dfd2;padding:29px;margin:24px 0;scroll-margin-top:20px}.section>p:first-of-type{margin-top:0}.notice{border-left:3px solid #b5965c;background:#f7f4eb;padding:15px 18px;margin:20px 0}.table-wrap{overflow:auto;margin:20px 0}table{border-collapse:collapse;width:100%;font-size:12px}caption{text-align:left;font-size:12px;color:#768477;margin-bottom:10px}th{background:#edf2e9;font-weight:600;white-space:nowrap}th,td{border-bottom:1px solid #dfe6da;padding:11px 10px;text-align:left;vertical-align:top;min-width:75px}td{font-variant-numeric:tabular-nums}tbody tr:nth-child(even){background:#fafbf7}.cite{display:inline-flex;gap:7px;margin-left:6px;font-size:11px}.source-meta{display:block;font-size:11px;color:#7a887e;margin:5px 0 13px}li{margin-bottom:10px}details{border-top:1px solid #dfe5d9;padding:12px 0}summary{cursor:pointer;font-weight:600}.layers{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.layer-tile{border:1px solid #c6d4c4;background:#f1f5ed;padding:14px;line-height:1.5}.layer-tile b{display:block;color:#315c46;font-size:17px}.layer-tile small{font-size:11px;color:#788579}.thesis{border-left:3px solid #678b68;padding-left:18px;margin:25px 0}.formula{font:12px/1.8 ui-monospace,monospace;background:#edf1e8;padding:15px;overflow-wrap:anywhere}.bar-row{display:grid;grid-template-columns:150px 1fr 90px;gap:10px;align-items:center;margin:11px 0;font-size:12px}.bar-track{height:15px;background:#f0f3ed}.bar{height:100%;background:#5d8066}.neg .bar{background:#b58162}.filter{border:1px solid #bdcbbd;padding:10px 14px;background:white;width:100%;max-width:440px;border-radius:3px;font:inherit}footer{padding:25px 0;color:#79867b;font-size:12px}svg{width:100%;height:auto;display:block}.warn{color:#946b38}.flow{border:1px solid #dce4d7;padding:16px;background:#fafbf7}p{margin:12px 0 18px}.compact{font-size:13px}.source-list{padding-left:22px}@media(max-width:1000px){.shell{grid-template-columns:175px minmax(0,1fr)}.report{padding:25px 20px}.kpis,.layers{grid-template-columns:repeat(2,1fr)}h1{font-size:29px}.section{padding:23px}}@media(max-width:640px){.shell{display:block}.toc{position:static;display:flex;flex-wrap:wrap;max-height:none;padding:16px;gap:8px}.toc a{border:1px solid #d0dacb;padding:6px 8px;margin:0;font-size:11px}.toc .n{display:none}.report{padding:12px 14px}.section{padding:20px 14px}.top{font-size:11px}.kpis{gap:8px}.kpi{padding:11px}.kpi b{font-size:21px}.layers{grid-template-columns:1fr 1fr}.bar-row{grid-template-columns:95px 1fr 65px}h1{font-size:27px}h2{font-size:21px}}@media print{body{background:white;font-size:10px}.top,.toc,.filter{display:none}.shell{display:block}.report{padding:0}.section{border:0;border-top:1px solid #bbb;margin:15px 0;padding:18px 0}.posture{background:#eee;color:#222}table{font-size:9px}.kpi{break-inside:avoid}h2,h3{break-after:avoid}a{color:inherit}}'''
JS="""document.querySelectorAll('[data-filter-table]').forEach(input=>input.addEventListener('input',()=>{const q=input.value.toLowerCase().trim();document.querySelectorAll('#'+input.dataset.filterTable+' tbody tr').forEach(row=>row.hidden=!row.textContent.toLowerCase().includes(q));}));"""

def page(title,subtitle,posture,posture_text,kpis,sections,sources,name):
 nav=''.join(f'<a href="#{E(s["id"])}"><span class="n">{i+1:02}</span>{E(s["title"])}</a>' for i,s in enumerate(sections))
 body=''.join(f'<section class="section" id="{E(s["id"])}"><p class="eyebrow">{i+1:02} / Research</p><h2>{E(s["title"])}</h2>{s["body"]}</section>' for i,s in enumerate(sections))
 stats=''.join(f'<div class="kpi"><label>{E(a)}</label><b>{b}</b><small>{E(c)}</small></div>' for a,b,c in kpis)
 html=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} · Personal Financial Analyses</title><meta name="description" content="{E(subtitle)}"><style>{CSS}</style></head><body><header class="top"><span class="brand">PFA / PERSONAL FINANCIAL ANALYSES</span><a href="/">返回研究平台 ↗</a></header><div class="shell"><nav class="toc" aria-label="报告目录">{nav}<a href="#sources">来源与版本</a></nav><main class="report"><p class="eyebrow">Deep research · 2026.10.25 · v1</p><h1>{E(title)}</h1><p class="deck">{E(subtitle)}</p><p class="meta">研究截止 2026-10-25 · 价格参考 2026-10-23 · 全球 / 美股、港股、A股 · 事实、公司说法、研究判断与条件测算分列</p><div class="posture"><strong>{E(posture)}</strong><p>{posture_text}</p></div><div class="kpis">{stats}</div>{body}<section id="sources" class="section"><h2>来源、核验与研究边界</h2><p>来源数字为已读原文中的选定字段；取得原件与算术勾稽不能替代会计审计、经营归因或前瞻验证。团队交叉审查属于同一AI体系，不是独立机构签字。未取得授权、同一时点的逐分析师一致预期，不称超预期或预测成功率。</p><ol class="source-list">{references(sources)}</ol><p class="meta">本稿v1保留本次信息截点。后续证据应生成新版本，并说明哪些判断改变；历史结论和错误不覆盖。</p></section><footer>Personal Financial Analyses · 个人中长期研究 · 无个性化仓位建议 · 尚未形成有证据承保的目标价</footer></main></div><script>{JS}</script></body></html>'''
 target=OUT/name;target.write_text(html)
 return dict(path=str(target.relative_to(ROOT)),sha256=hashlib.sha256(html.encode()).hexdigest())


def build_byd(b):
 sources=b['sources']+[
 dict(id='B17',title='工信部：2026年9月汽车工业经济运行',url='https://www.miit.gov.cn/gxsj/tjfx/zbgy/qc/art/2026/art_8a878aeeb8a34a5b88975c5bbe94f7bf.html',published_at='2026-10-12',period='2026-09及1—9月，含乘/商用车及出口',notes='统计口径不能直接与BYD全球乘用/商用批发混算零售份额。'),
 dict(id='B18',title='吉利：2026H1业绩官方摘要',url='https://www.geely.com/en/news/2026/geely-auto-record-h1-2026-revenue',published_at='2026-08-17',period='2026H1',notes='核心利润为公司调整指标，不能与BYD归母GAAP直接排名。'),
 dict(id='B19',title='Tesla Q3 2026 Update / 8-K',url='https://ir.tesla.com/_flysystem/s3/sec/000162828026066738/tsla-20261021-gen.pdf',published_at='2026-10-21',period='2026Q3',notes='公司定义FCF及FSD订阅口径；与BYD H1期间不同。')]
 c=lambda *ids:cite(ids,sources)
 facts={(f['metric'],f['period']):f for f in b['facts']};v=lambda key,period='2026H1':D(facts[(key,period)]['value'])
 cal=b['calculations'];cv=lambda k:D(cal[k]['value'])
 stats=[('H1归母净利润','123.25 亿元','同比−20.54% / 2026H1'),('Q2归母同比','+29.66%','累计相减；季度恢复可见'),('H1现金投入后','−73.68 亿元','CFO减全部现金Capex；非FCFE'),('H/A诊断TTM PE','19.09 / 25.33×','当前股数与10/23价格；非forward')]
 sec=[]
 sec.append(section('answer','先给研究判断',paragraph('比亚迪已有恢复的迹象，最有分量的证据是二季度利润和三季度销量；长期回报的决定点是恢复能否穿过库存、研发、海外投资和政策变化，最终形成普通股可获得的现金。当前姿态是<strong>有条件观察、继续研究</strong>。H股对应的盈利要求低于A股，但现有证据不足以给出低估结论。')+c('B01','B02','B04','B16')+table(['判断层','本轮看法','什么会改变判断'],[
 ['业务质量','规模、制造与电池整合、海外布局提供竞争基础；优势须体现为成本、毛利和资本回报','海外本地化后成本/质量/渠道优势持续，或持续回报走弱'],
 ['边际方向','Q2利润及Q3批发量恢复；Q3盈利仍未知','10/29结果能否证明利润与回款随量改善'],
 ['现金与资本','投入收缩缓和资金压力，营运资本融资仍重要','库存/应收释放，且应付支持减弱时仍能覆盖必要投入'],
 ['现价经济性','H股估值条件较低，仍需要稳定盈利和现金回报','正常化利润、完整资本桥与政策净暴露得到验证']])) )
 sec.append(section('business','从客户与竞争看业务',paragraph('集团由汽车及相关产品、手机部件和组装等业务组成。汽车优势来自电池、动力系统和制造整合、车型覆盖与渠道；这种整合降低外采依赖，也增加产能、研发和海外建厂的资金承诺。价格战中的胜出者仍可能为保住份额而消耗现金。')+table(['观察','原始事实/定义','研究含义'],[
 ['汽车及相关','H1收入2,753.41亿元、同比−8.98%；毛利率22.33%，上年20.35%','毛利率韧性支持结构/成本改善；量与价的分解仍需车型/地区净价。该分部还含电池等业务。'],
 ['电子与组装','H1收入694.05亿元、同比+0.96%；毛利率5.04%，同比−2.67个百分点','集团增长和盈利不能由汽车销量单独解释；AI服务器机会须证明分部毛利和现金。'],
 ['海外','集团境外收入占52.57%；汽车合同收入境外占约47.07%','两种分母不同。不能以集团海外占比替代汽车业务海外占比。']])+c('B02')+paragraph('行业也有分化：工信部/中汽协口径1—9月新能源汽车销量同比+11.1%，其中包含不同车型及出口；BYD全球批发同期−3.94%，提示需要解释竞争与结构，不能直接据此计算国内零售份额。吉利H1营收同比+15%、公司定义核心归母利润+46%，说明行业压力并非均匀分布。Tesla Q3归母净利7.87亿美元、CFO62.63亿美元、现金Capex47.32亿美元，反映利润和现金可能异向；其软件/能源业务及期间与BYD不同，不直接排利润率高低。')+c('B04','B17','B18','B19')))
 rows=[]
 for name,key in [('营业收入','revenue'),('归母净利润','parent_net_income'),('经营现金流','CFO'),('现金Capex','cash_capex'),('研发总投入','R&D_total')]:
  a,p=v(key),v(key,'2025H1');rows.append([name,yi(p),yi(a),pct(a/p-1)])
 rows += [['Q2归母净利（派生）',yi(cv('Q2_prior_parent_NI')),yi(cv('Q2_parent_NI')),pct(cv('Q2_parent_NI_yoy'))],['Q3新能源车批发量（万辆）',fmt(cv('Q3_prior_NEV_units')/10000),fmt(cv('Q3_NEV_units')/10000),pct(cv('Q3_unit_yoy'))]]
 sec.append(section('actuals','实际经营：先拆季度再看恢复',table(['指标','2025同期','2026本期','同比'],rows,'财务金额为亿元人民币；H1为1—6月；Q2/H1−Q1，Q3销量/9M−H1。')+c('B02','B03','B04','B16')+paragraph('H1总数仍弱，不能抹去Q2的正面反证。9月销量46.36万辆、同比+16.98%，三季度累计同比+18.75%；这支持边际修复，但批发和出口不等于终端零售，销量也不决定单车利润。增长是否靠降价、渠道库存或高成本海外拓展，必须在利润、营运资本和后续终端数据中验证。')+note('<strong>信息截止：</strong>10/14公告安排10/29董事会审议三季报。当前知道Q3销量，不知道Q3利润、毛利和现金；不能把即将公布的业绩当作已有事实。')+c('B05')))
 wc=cv('working_capital_three_item_effect');before=cv('H1_cash_before_three_wc_items');ni=v('consolidated_net_income');noncash=before-ni
 capchange=v('cash_capex','2025H1')-v('cash_capex');improve=cv('H1_cash_after_total_capex')-cv('H1_2025_cash_after_total_capex')
 sec.append(section('cash','盈利→营运资本→现金→融资',table(['现金桥 / H1','亿元人民币','解释'],[
 ['合并净利润（含少数）',yi(ni),'CFO补充表起点，与归母口径分开'],
 ['非现金与其他调整合计',yi(noncash),'折旧/摊销/减值、财务/投资、税等原文调整项合计'],
 ['存货占款',yi(v('working_capital_inventory_effect')),'现金补充表，不等于期末库存账面增量'],
 ['经营应收变化',yi(v('working_capital_receivables_effect')),'按补充表现金口径'],
 ['经营应付增加',yi(v('working_capital_payables_effect')),'重要经营融资来源；不能默认永久增长'],
 ['经营现金流',yi(v('CFO')),'补充表逐项精确勾稽'],
 ['减：全部现金资本开支',yi(-v('cash_capex')),'购建固定、无形及其他长期资产现金'],
 ['现金投入后差额',yi(cv('H1_cash_after_total_capex')),'筛查现金指标，非维持性FCF/可分配FCFE']])+c('B02')+paragraph(f'相对上年同期，现金投入后差额改善{yi(improve)}亿元，其中现金Capex减少{yi(capchange)}亿元，约解释改善的{pct(capchange/improve)}。改善主要由支出收缩贡献；降低投入是否损害未来产能/技术，需要追踪各项目回报，不能仅把现金改善视为需求已转强。')+paragraph('库存净额从年末1,384.21亿元升至1,899.91亿元。库存/经营应收/经营应付三项合计净占款149.40亿元，所以“应付贡献现金”并不等于全部营运资本在释放，也不证明存在逾期或违约。公司需要解释海外备货、车型切换、备料和真实终端去化。')+table(['其他资金桥','亿元人民币'],[['期初现金及等价物','683.95'],['经营现金流','+373.35'],['投资活动现金流','−555.70'],['融资活动现金流','+63.88'],['汇率对现金影响','−9.28'],['期末现金及等价物','556.19']])+paragraph('损益表汇兑损失47.03亿元与现金汇率影响−9.28亿元是不同口径。资本化研发55.54亿元为发生额，未取得独立现金组成时，不能在447.03亿元总现金Capex之外再扣一次。')))
 sec.append(section('quality','正常化盈利：汇兑、研发和补助一起审议',table(['项目','事实或计算','判断边界'],[
 ['汇兑损益','本期损失47.03亿元、上年收益31.60亿元；同比税前拖累78.63亿元','不应直接把所有损失加回并假定未来不再发生；净外汇敞口/套保需补证。'],
 ['研发资本化','55.54亿元 vs 12.84亿元；资本化率19.24% vs 4.16%','费用确认时点改变。需项目经济寿命、后续摊销与失败项目减值；不是由资本化上升直接断言造假。'],
 ['政府支持','其他收益确认政府补助67.26亿元','现金取得/利润确认、项目条件和持续性要分开；不能无条件永久化，也不能全部归零。']])+c('B02')+paragraph('一个能改变结论的双向检验：剔除当期汇兑损益后，税前利润同比增量约35.67亿元；同期研发资本化发生额增量42.70亿元。如果仅将当期资本化发生额费用化，这个增量会转为约−7.03亿元。但该测算尚未加回历史相关摊销、处理税和归属，所以它证明<strong>方向仍需核验</strong>，不是已确定的正常化利润。')+note('“扣非净利”也不自动等于所有者收益。研发经济成本、维持投入、必要营运资本与融资约束仍应分别审议。')))
 sec.append(section('capital','资本、债务与普通股的索偿',table(['2026-06-30项目','亿元人民币','不能混淆的口径'],[
 ['现金及等价物','556.19','已排除相应受限款的口径不能再重复扣受限货币'],
 ['交易性金融资产','699.40','产品期限、流动性及限制未完整承保，不能全数当即时可分配现金'],
 ['有息/融资负债（含租赁）','1,309.27','按现金流补充表期初期末融资负债分类汇总，流动/非流动不重复加'],
 ['其他权益工具/永续','208.47','会计列权益仍可能影响分配、重置和赎回；不是普通股零成本资金'],
 ['应付贸易款 / 贸易票据','1,763.56 / 534.13','经营索偿也影响生存与现金；不能仅用债券衡量付款压力'],
 ['应付债券（非流动）','149.94','与应付票据534.13亿元分开'],
 ['质保等预计负债','340.44','产品规模带来长期履约成本与估计风险']])+c('B02')+paragraph('现金及可变现资产提供资金缓冲，现有资料不支持“即将失去偿付能力”的断言；同样，“账上资产多”也不足以证明有大量可自由分配现金。只用现金等价物扣融资负债得到的753.08亿元净融资负债，只是保守口径诊断，尚未计入理财可变现性、永续、少数股东与交割时点，不能当成当前完整EV桥。')+note('<strong>存量台账语义修正：</strong>旧字段 notes_payable 的149.94亿元实际指“应付债券”，不是“应付票据”。本稿按原文中文项目分别列示，旧版保留。错误发现来自附注深读，不由文件哈希自动保证。')))
 sec.append(section('policy','政策与海外：先确认税基和生效时间',table(['事件','当前状态','进入模型的方法'],[
 ['2026—2027购置税减半','已生效；每车减税上限15,000元','消费者总成本→销量/促销分担→国内收入、毛利与现金，不能一比一映射公司净利'],
 ['新能源汽车出口退税13%→9%','10/12已公告，2027-04-01起生效','适用中国出口FOB税基×4个百分点×不可转嫁比例，按实际出口日期/产品目录'],
 ['中欧混动/BEV安排及价格承诺','原则/程序已公布；公司配额与具体实施未完全确认','车型、地区、价格承诺及本地制造成本；不把媒体配额或历史17%税率机械外推']])+c('B07','B08','B09','B10','B11','B12')+paragraph('每1,000亿元合规FOB销售税基，若完整适用新税率、公司承担全部差额，税前敏感性为40亿元；承担一半为20亿元。这里的1,000亿元和承担比例是分析假设，并非已知BYD暴露。集团境外收入含电子、当地制造及不同税基，不能直接套用；2027年也不能不分出口日期就按全年冲击计算。')+paragraph('四月生效前还可能出现报关/渠道前置。需把出厂、报关、海外经销商库存与终端注册拆开，避免将政策切换前的出货年化成持续需求。')))
 share_rows=[['A股','002594.SZ','81.42 CNY','5,433,797,565'],['H股','1211.HK','71.60 HKD','3,683,400,000']]
 reverse=[[r['assumed_PE']+'×',yi(r['common_profit_required_A_CNY']),yi(r['common_profit_required_H_CNY'])] for r in b['reverse_price_conditions']]
 sec.append(section('valuation','A/H定价、反推条件与敏感性',table(['证券','代码','10/23参考收盘','9/30分类股数'],share_rows)+c('B06','B13','B14','B15')+paragraph('同日官方中间价为1港元=0.85696人民币（不是同一瞬间可成交的收盘FX）。H股折合61.36元，A股溢价32.70%；两地资金准入、交易成本、税费、流动性和风险溢价不同，价格差不自动构成可执行套利。')+paragraph('TTM归母利润294.34亿元，扣限制性股份利润与其他权益工具分配后，基本EPS利润分子293.10亿元；除当前总发行股数91.17198亿得到诊断每股盈利3.21483元。它不是公司披露的精确滚动加权稀释EPS。由此A/H诊断TTM PE约25.33/19.09倍。真实A/H分价加总股权市值约6,684.27亿元人民币；H股类别市值2,637.31亿港元不能当集团市值。')+c('B01','B02','B06')+table(['假设估值倍数','A股现价要求的年度普通股利润 / 亿元','H股现价要求 / 亿元'],reverse,'价格反推的条件，不代表投资者共识，也不代表我们认定该倍数合理。')+table(['年度普通股利润假设','PE15× CNY / HKD','PE20× CNY / HKD','PE25× CNY / HKD'],[[str(profit)+'亿元']+[fmt(D(profit)*D('1e8')*D(pe)/D('9117197565'))+' / '+fmt(D(profit)*D('1e8')*D(pe)/D('9117197565')/D('.85696')) for pe in (15,20,25)] for profit in (200,300,400)],'纯条件敏感性；未指定基准概率/期限，不是目标价，未完成的经营/融资模型不能被矩阵替代。')+paragraph('在假设20倍下，A股要求约371.16亿元可持续普通股利润，H股约279.71亿元。应继续问：这些利润在必要研发、库存融资、海外工厂和退税调整后能转成多少现金，是否需要新增普通股/永续资金，以及增长还能持续多久。当前未取得同日授权共识和完整正常化预测，不能宣称超预期或低估。')))
 stresses=[]
 for beta in (D(0),D('.5'),D(1)):
  cf=v('CFO')-beta*v('working_capital_payables_effect');stresses.append([pct(beta),yi(cf),yi(cf-v('cash_capex'))])
 sec.append(section('opposition','最强反方与先坏在哪里',table(['主解释','最强替代解释','区分两者的观察'],[
 ['Q2及Q3代表经营修复','降价/渠道前置、资本化费用及低投资暂时提高表现','10/29汽车经营利润、研发经济成本、现金回款与终端去化同时改善'],
 ['海外提高盈利韧性','关税/退税/本地制造与渠道成本吞掉增量回报','地区净价、当地成本、经销库存与项目cohort ROIC'],
 ['CFO改善降低风险','资本开支收缩及新增应付贡献难长期维持','投入恢复后、付款趋正常时仍保持现金资本回报'],
 ['H股较A股便宜值得重估','较低倍数反映盈利/政策/资本风险，盈利与倍数可能同降','正常化普通股利润在不利政策和融资条件下仍达到反推门槛']])+table(['新增经营应付贡献消失的比例假设','其他不变下CFO / 亿元','再减原现金Capex / 亿元'],stresses,'冻结其他变量的流动性压力诊断；不是预测应付款会逆转，也不是要求偿还全部现有应付。')+paragraph('首先失效的链条可能是净价/组合→利润，再通过库存和账期转成现金缺口；也可能是政策/并网建厂延迟使投资先发生而回报后移。供应商融资、理财变现和其他权益工具都应在同一资金期限表中检查。不能只给股价下跌的百分比而不解释损失机制。')))
 sec.append(section('monitor','下一证据、提醒与方法交叉验证',table(['频率/窗口','重点观察','研究提醒/动作'],[[E(m['frequency']),E(m['metric']),E(m['trigger'])+'；'+E(m['action'])] for m in b['monitoring']])+table(['方法','怎样应用到本案','本轮结论'],[
 ['所有者收益/资本回报','把净利润拆到必要营运资本、投入与普通股分配','总现金Capex含增长，负差额不自动等于企业无价值；维持投入仍未知'],
 ['逆向思考/激励','同时检查坏的汇兑与有利的费用资本化，承认季度恢复反证','避免单边加回或先定正负方向再选证据'],
 ['价格与预期','按股本、币种和同口径盈利反推当前要求','H股条件较低；尚未完成可持续利润与融资后回报验证'],
 ['永久损失视角','检查量价、库存、供应商融资、政策与资本支出联合恶化','提醒触发研究重审，不自动生成买卖/仓位指令']])+paragraph('仍优先补：车型/地区净价与终端库存，海外项目利用率和融资后资本回报，研发项目摊销/现金分类，以及公司级贸易与出口退税净暴露。报表事实及已列算术把握较高；经营机制把握中等；当前估值与未来预测把握较低。监测阈值属于研究筛查，未完成前瞻校准。')))
 return page('比亚迪：恢复、现金与A/H定价','从量价成本和季度变化出发，穿透研发、营运资本、海外政策、融资与普通股回报。','存在边际恢复证据；现金回报与现价结论继续核验','Q2利润和Q3销量值得正视；当前最重要的验证点是10/29财报，以及2027年出口退税变化下的净盈利和资金暴露。',stats,sec,sources,'byd-deep-dive.html')

def build_ai(infra,apps,valuation,market):
 sources=[]
 titles={'IEA26':'IEA：2026能源与AI关键问题','NVDA27Q2':'NVIDIA FY27 Q2业绩','NVDA26FY':'NVIDIA FY26全年业绩','AVGO26Q3':'Broadcom FY26 Q3业绩','AVGO25FY':'Broadcom FY25全年业绩','TSMC26Q3':'TSMC 2026Q3业绩','TSMC26CALL':'TSMC 2026Q3官方电话会','MU26FY':'Micron FY26全年业绩','VRT26Q2':'Vertiv 2026Q2业绩','VRT25FY':'Vertiv 2025全年业绩','VRT26Q3DATE':'Vertiv下次财报日期','ETN26Q2':'Eaton 2026Q2业绩','ETN25FY':'Eaton 2025全年业绩','GEV26Q2':'GE Vernova 2026Q2业绩','CEG26Q2':'Constellation 2026Q2业绩','CRWV26Q2':'CoreWeave 2026Q2业绩','CRWV26Q2FILING':'CoreWeave 2026Q2 10-Q','GDS26Q2':'GDS 2026Q2业绩','ENVICOOL26H1':'英维克2026半年报','HYGON26Q3':'海光信息2026三季报'}
 for s in infra['source_register']:
  sources.append({**s,'title':titles.get(s['id'],s['id']),'notes':s.get('interest','')})
 for s in apps['sources']:
  s=dict(s)
  if s['id']=='pltr-q2':s.update(url='https://www.sec.gov/Archives/edgar/data/1321655/000132165526000039/a2026q2ex991pressrelease.htm',notes='原IR地址返回脚本壳；补读SEC正式业绩附件，核实选定字段。')
  sources.append(s)
 sources += [dict(id='GS26',title='Goldman Sachs：AI瓶颈与资本建设',published_at='2026-10-19',period='2026—2031预测；非已发生投入',url='https://www.goldmansachs.com/what-we-do/investment-banking/insights/articles/navigating-a-system-of-ai-bottlenecks',notes='投行公开观点，存在融资业务利益；本稿不冒充取得完整卖方模型。'),dict(id='MS26',title='Morgan Stanley Institute：AI市场趋势',published_at='2026-03-09',period='2025—2028数据中心建设融资预测',url='https://www.morganstanley.com/insights/articles/ai-market-trends-institute-2026',notes='页面明确非FINRA研究报告；范围/年份与GS不同。'),dict(id='FED26',title='FOMC 2026-09-16声明',published_at='2026-09-16',period='当时政策决定，非未来利率预测',url='https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm'),dict(id='FEDCAL',title='美联储FOMC官方日历',published_at='持续更新，截止10/25读取',period='2026年会议安排',url='https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'),dict(id='AMZCAL',title='Amazon Q3财报安排',published_at='2026-10',period='10/29预定事件',url='https://www.aboutamazon.com/news/company-news/amazon-earnings-q3-2026-report')]
 c=lambda *ids:cite(ids,sources)
 sec=[]
 sec.append(section('answer','研究结论：增长、利润和股权回报分开',paragraph('AI已经产生可核实的芯片收入、云分部经营利润和部分应用现金流；同时，新增资本承诺、模型融资和GPU租赁的资金消耗非常大。当前应逐层追问：<strong>谁掌握稀缺资源，谁为谁付钱，终端客户是否愿意持续付费，以及现价已经要求多高的增长。</strong>')+table(['层面','当前判断','最强反证/改变条件'],[
 ['算力与电气设施','已有真实利润和供给约束；收入确认和合同兑现较模型层更可观察','若客户资本支出放缓、预约取消、预付款逆转或供给追上，利润与现金可能同时恶化'],
 ['云与平台','云经营利润证明存在付费需求；全集团仍承担建设和共享研发费用','强客户回款、可用容量、成熟资产回报与低价推理需求可使扩张自我融资'],
 ['基础模型与新云','收入增长和融资规模可见，融资后普通股回报尚难验证','单位任务成本下降、持续收费、独立客户回款及更低资本强度可改善判断'],
 ['应用','工作流、权限、专有数据与续费是优势候选；纯包装功能更易被平台捆绑','毛利扣除推理/实施/人工复核后仍改善，且客户能证明节约或增收'],
 ['证券价格','已取得40个标的10/23参考价格；仅4家完成本轮TTM诊断','完整稀释资本表、正常化利润、未来现金流与价格联动仍需逐公司承保']])+paragraph('因此，本稿没有给AI整体“看多/看空”的统一评级。优先深入研究的是已有现金回报且优势可验证的节点；优先风险审查的是短期债务、重投入、客户集中和融资依赖叠加的节点。两者都不等于现价买卖结论。')+c('NVDA27Q2','goog-q2','CRWV26Q2','pltr-q2')))
 layers=[
 ('00','能源/电网/储能','CEG、GEV、ETN；A股国电南瑞/思源电气/阳光电源为扩展观察','发电商看净电价、交付和燃料；电网设备看订单毛利/现金；储能看价差、循环与安全','已获批/已通电MW、PPA起始年、客户预付、项目融资；不能用GW预约直接当本期收入'),
 ('01','数据中心/电气/冷却','VRT、GDS；英维克','每MW租金与占用、配电/液冷产品毛利、维持投入后回报','已开工→通电→上架→计费；交付/取消条款、订单转收入及定金是否会退'),
 ('02','GPU/ASIC/CPU','NVDA、AVGO；AMD/海光/寒武纪','软件生态、性能/成本、客户集中、定制芯片替代、供应限制','产品代际切换、库存/应收、价格与毛利、客户采购是否靠融资'),
 ('03','制造/存储/互联','TSM、MU；ANET、中际旭创/新易盛/中芯国际/工业富联为扩展','先进制程/封装、HBM良率、网络瓶颈；高景气利润须按周期审视','产能/交期/良率、长约价格、客户重叠、库存；集团非AI业务分开'),
 ('04','云/算力租赁','MSFT、AMZN、GOOGL；阿里/腾讯/百度；CRWV','可用GPU时×付费利用率×实现租价，减全生命周期成本；云还有软件服务','RPO/预付不等于当期外部需求；折旧、租赁、资本支出、债务到期及回款'),
 ('05','基础模型','OpenAI/Anthropic私募；MiniMax/智谱港股；xAI属SPCX','每个合格任务的收入、推理/训练/数据/服务成本、价格竞争、品牌与分发','ARR/年化/月收入不能当GAAP年收入；融资承诺、实际现金、可转债和优先权'),
 ('06','数据/开发/治理','Databricks私募；ORCL及云平台为交叉观察','数据治理、权限、迁移与开发依赖；评测/观测/安全价值须落到合同','客户留存、平台捆绑、服务成本及可替换性；ORCL未完成本轮财务承保'),
 ('07','应用/Agent/终端','PLTR、NOW、CRM、ADBE；金山办公/讯飞；智能车为延伸','收入按席位/用量/结果兑现；业务集成和分发影响护城河','付费留存、扩张率、可核验客户ROI、失败/人工接管、推理后毛利与现金')]
 tiles='<div class="layers">'+''.join(f'<div class="layer-tile"><small>LAYER {i}</small><b>{E(n)}</b><small>{E(reps)}</small></div>' for i,n,reps,_,__ in layers)+'</div>'
 sec.append(section('map','自底向上：八层产业与资本市场地图',tiles+table(['层级/公开市场映射','谁赚什么钱','关键验证'],[[i+' '+n+'<br><small>'+E(reps)+'</small>',E(econ),E(watch)] for i,n,reps,econ,watch in layers])+note('“扩展观察”只证明研究位置，不代表本轮完成该公司的财报、估值或技术竞争核验。A/H/美股同名业务并不自动具有同样经济暴露；投资云巨头也不等于直接拥有其模型投资全部价值。')))
 sec.append(section('energy','能源是地点、时间与交付问题',paragraph('IEA在2026年4月更新中估计：全球数据中心用电由2025年的485TWh升至2030年的950TWh，后者约占全球电力3%。这是<strong>全体数据中心、2030年预测</strong>，不是已发生的纯AI耗电。全球电量够用也不能解决某个园区在某一年能否接入电网。')+c('IEA26')+table(['变量','如何传导到盈利和估值','当前可核查事实'],[
 ['电力与并网','通电晚→GPU不能计费→利息/租金先支付；电价是否可转嫁决定成本归属','CEG新增920MW长约交付预计2029—2032；不能记作2026新增AI电力收入。核电重启另有许可和执行风险。'],
 ['燃机与设备','短缺可支持价格与预付；新供给和取消会反向作用','GEV Q2所述116GW由53GW正式积压与63GW产位预约组成；两者承诺强度不同。'],
 ['配电与冷却','高功率密度拉动产品组合，安装/保修/竞争会影响兑现','ETN Q2美洲电气滚动订单+41%、积压+43%；VRT H1递延收入贡献现金，须看后续履约成本。'],
 ['储能与电网调节','平移发电时段、提供容量/辅助服务；收益依赖电价机制与循环寿命','MW为功率，MWh为能量；储能不是凭空增加基荷。BYD储能不能由集团汽车销量推断独立利润。']])+c('CEG26Q2','GEV26Q2','ETN26Q2','VRT26Q2')+paragraph('单位演算：1GW IT负载、PUE 1.2、全年满电负载需要10.512TWh；若电负载率80%，为8.4096TWh。IT负载与园区总负载、用电负载率与GPU计费利用率不能互换。用核电/燃机概念股票表达AI观点时，还要扣除建设、燃料、监管获准回报和融资条件。')))
 sec.append(section('infra','芯片、制造、冷却：真实盈利与周期风险',table(['公司 / 最新已公布期间','经营锚点','判断与反方'],[
 ['NVIDIA / FY27Q2 截7/26','收入962.21亿美元；数据中心890亿美元；GAAP毛利率75%；EPS2.46美元','已有强经营利润。Q3收入1,080亿美元±2%是指引；不能用增长或PE单独判便宜。'],
 ['Broadcom / FY26Q3 截8/2','收入295.91亿美元；公司定义AI半导体167亿美元；CFO141.97亿美元','定制芯片/互联受益；集团还含VMware。AI客户集中和自研替代需跟踪，不能给全公司套纯AI估值。'],
 ['TSMC / Q3 截9/30','收入467.2亿美元；毛利率66.4%；普通股EPS新台币29.43 / ADR EPS4.60美元','先进制造稀缺；海外扩产、地缘与客户资本周期影响回报。Q4收入523—543亿美元为指引。'],
 ['Micron / FY26Q4 截9/3','收入542.29亿美元；GAAP毛利率86.8%；CFO439.73亿美元','非常强的景气利润；集团含DRAM/NAND等，周期顶部低PE不等于安全边际。'],
 ['Vertiv / Q2 截6/30','收入32.743亿美元；GAAP经营利润6.379亿美元；H1 CFO18.666亿美元','H1递延收入增加18.227亿美元，大额预收增强现金同时带来履约义务；10/28Q3尚未公布。'],
 ['Eaton / Q2 截6/30','集团收入85.31亿美元；GAAP EPS2.11 / 调整后3.15美元','订单与产品组合支撑；集团非AI分部、并购、调整项与股数须独立核对。'],
 ['GDS / Q2 截6/30','收入30.88亿元人民币；毛利率21.5%，上年23.8%','净利8.38亿元含权益法收益9.60亿元，主要与DayOne融资摊薄收益有关；利润增长不能替代运营现金。'],
 ['英维克 / H1','收入30.17亿元人民币，同比+17.24%；归母1.85亿元，同比−14.32%；CFO0.62亿元','热管理需求增长与股东利润可以背离；竞争、产品/客户结构和回款比概念纯度重要。'],
 ['海光信息 / 9M 截9/30','收入149.55亿元；归母28.47亿元；CFO−24.43亿元；研发44.72亿元','国产算力需求有财务支持；收入增长同时占用现金，高研发和供应约束仍需融资/项目回收检验。']])+c('NVDA27Q2','AVGO26Q3','TSMC26Q3','MU26FY','VRT26Q2','ETN26Q2','GDS26Q2','ENVICOOL26H1','HYGON26Q3')+paragraph('以上不是同期间利润率排行榜。美国财年、自然季度、半年与九个月不同；报表币种也不同。TSMC不能把台股每股盈利直接除以美股ADR价格。光模块、服务器组装与国产芯片的其余观察标的尚未完成逐家公司交叉核验，不从行业热度推断它们的实际AI利润。')))
 sec.append(section('cloud','云的现金账：谁在为扩张付款',table(['公司 / 期间','经营验证','现金投入与会计警报'],[
 ['MSFT / FY26Q4 截6/30','收入900.07亿美元、经营利润406.03亿美元','全年CFO1,829.35−现金PPE1,159.48=669.87亿美元。Q4含新融资租赁CapEx约410亿美元，不能直接与现金PPE相加。'],
 ['Alphabet / Q2 截6/30','Cloud收入248亿美元、经营利润88.14亿美元；合并经营利润407.70亿美元','Q2 CFO390.69−现金PPE449.24=−58.55亿美元；TTM差额532.73亿美元。合并净利含巨额投资收益。'],
 ['Amazon / Q2 截6/30','AWS收入422.32亿美元、经营利润166.21亿美元','TTM CFO1,614亿美元，按公司定义FCF−76亿美元；本季净利含税前534亿美元、主要为Anthropic投资收益。'],
 ['Meta / Q3 截9/30，10/21已发布','收入646.01亿美元；经营利润129.88亿美元含98.9亿美元诉讼支出','Q3 CFO327.9−含融资租赁本金CapEx349.1=−21.2亿美元。广告展示/价格改善存在，不能归因全部AI。'],
 ['阿里 / 6月季度，新分部','AI Cloud & Compute收入484.37亿元，调整EBITA56.28亿元；AI Labs & Applications收入33.38亿元，调整EBITA−138.61亿元','CFO229.45亿元；公司定义FCF−446.70亿元；8/26完成发行7.1亿股，毛额800亿港元。云与模型现金回报不同。'],
 ['腾讯 / Q2','集团收入2,047.85亿元，经营利润672.76亿元','Q2 CFO527−CapEx593−内容50−租赁22≈公司FCF−138亿元；剔除计算资源预付的+376亿元不撤销实际付款。'],
 ['百度 / Q2','AI云收入73亿元，同比+50%、环比−17%；传统业务104亿元，同比−23%','CFO34.36−现金CapEx113.90=−79.54亿元人民币。集团增长和AI分类增长必须分开。']])+c('msft-q4','msft-call','goog-q2','amzn-q2','meta-q3','baba-q1','baba-placing','tencent-h1','bidu-q2')+paragraph('三项容易改变结论的核对：Alphabet合并净利1,121.93亿美元、普通股分子1,121.07亿美元，税前其他收益979.83亿美元；不能将税前投资收益直接从税后净利中相减来制造“正常化利润”。Cloud分部利润又未承担集团层共享AI研发等全部成本。Microsoft FY27建筑使用寿命15→25年、部分租赁呈列改变，使其CY26披露CapEx指引1750亿美元低于原1900亿美元，但公司称经济投入不变；这不是GPU寿命变成25年或明确削减建设。')+c('goog-q2','msft-call')+paragraph('这些现金差额不是等价的股东自由现金流：资本支出、租赁本金、预付算力、内容资产的定义不同；必要投入、增长投入和营运资本时点尚未全部拆开。不能将不同公司的负FCF简单排名为财务危机，也不能将投资账面收益当现金融资能力。')))
 sec.append(section('models','模型公司的资本状态：上市、融资与损失',table(['主体 / 当前资本身份','官方披露锚点','股东层面需要核验'],[
 ['OpenAI / 私募','3/31宣布1,220亿美元承诺融资、投后8,520亿美元；月收入20亿美元为发行人说法','承诺并非全到账；月收入不是审计年收入。IPO讨论不等于完成上市；优先权、算力承诺和完整现金流未取得。'],
 ['Anthropic / 私募，已秘密递表','5/28 H轮650亿美元，投后9,650亿美元；年化收入470亿美元为公司说法；6/1宣布秘密S-1','650亿美元含此前150亿美元超大云厂承诺，不能再加一遍；年化run-rate不能当GAAP全年收入/利润。'],
 ['xAI / 已并入上市SpaceX','2/2并入SpaceX；SpaceX 6/11IPO定价135美元、6/12开始交易SPCX','当前不存在独立xAI股票价格。SPCX同时含航天/卫星等，不是模型业务的纯估值。'],
 ['MiniMax / 00100.HK','1/9上市；H1收入1.16573亿美元、毛利率17.9%；研发2.9687亿美元、期内亏损3.57997亿美元','高增长未覆盖研发与服务成本；广义现金13.228亿美元不等于无约束现金，也不能用亏损直接计算跑道。'],
 ['智谱 / 02513.HK','H1收入9.53892亿元人民币，毛利2.51611亿元；研发21.31171亿元、亏损20.71992亿元；API占86.5%','9月完成配售2,196.5万股；另有人民币201.4亿元、美元结算零息可转债到期2027，不能遗漏融资和潜在稀释。'],
 ['DeepSeek / 本轮未确认可交易证券','未取得截至截点的完整融资、收入和审计现金证据','不沿用旧的“从未融资”或传闻估值，也不假定技术声誉等于普通股可投价值。'],
 ['Databricks / 私募数据平台','8/13宣布50亿美元融资、1,900亿美元估值、70亿美元收入run-rate','这是发行人融资和年化指标；没有直接可交易普通股与完整公开GAAP资本桥。']])+c('openai-round','anthropic-round','anthropic-s1','xai-acquisition','spacex-ipo','minimax-ipo','minimax-h1','zai-h1','zai-financing-complete','dbx-aug')+paragraph('智谱的细节特别重要：配售后实际股份487,588,090股；可转债全转的备考股份513,953,116股并非已发行股数。转股价892.50港元高于10/23参考价499港元，这不预言未来股价，但说明不能默认自动转股消除2027年的美元偿付/再融资风险。私募投后估值、公司现有市值和“全稀释备考股数”也不能混为一个口径。')+c('zai-financing-terms','zai-financing-complete')+note('私募融资中的优先清算、分期到账、循环投资和云采购条款，可能让公布估值与普通股经济价值明显不同。没有这些条款与现金表，本稿不计算看似精确的模型公司P/E或资金跑道。')))
 sec.append(section('apps','应用与Agent：从调用量走到客户价值',table(['公司 / 最新期间','已验证经营证据','收入质量与成本审查'],[
 ['Palantir / Q2','收入19.35464亿美元、同比+93%；美国商业7.64亿美元、+149%；GAAP经营利润9.12004亿美元','CFO12.16167亿美元；调整FCF12.20359亿美元。集团还含政府和传统业务，不是纯AI。合同选项/可终止部分不能当必然兑现收入。'],
 ['ServiceNow / Q2','收入39.87亿美元；GAAP经营利润1.62亿美元 vs调整11.73亿美元','CFO5.87−PPE1.14=4.73亿美元；调整FCF6.34亿美元含并购现金费用加回。AI ACV超10亿美元不等于AI收入。'],
 ['Salesforce / FY27Q2','收入113亿美元，其中Informatica4.56亿美元；GAAP经营利润率20.5% vs调整34.1%','Agentforce/Data360 ARR约39亿美元含扩围；投资收益26.13亿美元、SBC9.06亿美元。债务支持250亿美元加速回购需纳入资本桥。'],
 ['Adobe / FY26Q3','收入67.6亿美元，GAAP经营利润23.54亿美元，CFO25.2亿美元','AI-first ARR增长>150%但未给金额基数；不能反推已实现AI收入。创作工作流与分发有价值，新增付费和替代风险仍需客户证据。'],
 ['金山办公 / H1','收入33.13亿元人民币+24.69%；归母25.18亿元+236.94%；CFO6.43亿元−12.96%','扣非仍有基金投资收益；公司调整利润10.87亿元也有SBC等加回。WPS365收入4.97亿元含协作等，不是纯AI。'],
 ['科大讯飞 / 9M','收入181.87亿元+7.05%；归母0.22亿元；扣非−7.63亿元','CFO2.64−长期资产现金34.78=−32.14亿元；融资现金净额60.59亿元。4月定增约39.81亿元净现金，单季盈利不证明自我造血。']])+c('pltr-q2','now-q2','crm-q2','adbe-q3','kingsoft-h1','iflytek-q3')+paragraph('判断应用护城河，要检验客户是否将它嵌入有权限、数据和责任边界的关键流程，切换成本是否真实，以及续费来自实际收益还是试用预算。应用能换底层模型是潜在议价优势；模型厂商进入应用、办公套件免费捆绑是反方。AI标识、下载量、调用量或排行榜领先都不能单独证明利润。')+table(['一项业务任务的账','应采的数据','研究触发'],[
 ['客户单位收益','完成质量合格的任务数×节省人工/增收；减错误、延迟、合规与切换损失','使用上升但接受率/续费/客户收益下降，重审价值创造'],
 ['应用单位贡献','实际收费−模型token−工具调用−检索/存储−重试−人工复核−支持成本','按坐席收费但Agent调用激增，毛利可能下降；按结果收费需承担失败风险'],
 ['可持续留存','付费cohort续费、扩张/流失、赠送/折扣、实施费用与收款','缺cohort或AI单独收入时标为未知，不用集团增长替代']])) )
 prices={r['symbol']:D(r['price']).quantize(D('.01')) for r in market['rows'] if r['status']=='observed'}
 vals=[];reverse=[];diagnostics=[]
 fcf_nv=D('126886000000')
 for row in valuation:
  symbol=row['symbol'];p=prices[symbol];eps=D(row['ttm_gaap_diluted_eps_quarter_sum']);cap=p*D(row['actual_shares']['val']);fcf=fcf_nv if symbol=='NVDA' else D(row['ttm_cfo_minus_cash_capex'])
  vals.append([symbol,fmt(p),row['latest_period_end'],row['actual_shares']['end'],fmt(cap/D('1e9')),fmt(eps),fmt(p/eps)+'×',pct(fcf/cap)])
  req=p*D('1.1')**3/D(25);g=(req/eps)**(D(1)/D(3))-1
  reverse.append([symbol,fmt(req),pct(g),'末期PE25×、3年价格年回报10%；不含股息/回购'])
  diagnostics.append(dict(symbol=symbol,price=str(p),eps=str(eps),market_cap_proxy=str(cap),reported_pe=str(p/eps),cash_yield_proxy=str(fcf/cap),reverse_terminal_eps=str(req),reverse_cagr=str(g),terminal_pe='25',price_return='0.1',horizon_years=3))
 sec.append(section('valuation','资本市场定价：先反推现价要求',table(['股票','10/23 USD','TTM终点','股数日期','市值代理 USD bn','4季EPS USD','历史PE','现金差额/市值'],vals,'价格取Yahoo参考日值；股数为最新报表披露实际股数，早于价格日；不是当日全稀释市值/完整EV。')+c('NVDA27Q2','NVDA26FY','AVGO26Q3','AVGO25FY','VRT26Q2','VRT25FY','ETN26Q2','ETN25FY')+paragraph('TTM报表项用上一全年+本年累计−上年同期，EPS为连续四季已报告稀释EPS之和，存在各季加权股数与四舍五入差异；未将一个高景气季度乘四。NVDA现金差额采用公司FCF定义（含相关资产本金），其余三家为CFO减现金PPE，均非已经承保的可分配现金。股数/财报滞后、期权/可转债、融资租赁、SBC与投资税项仍限制横向比较。')+paragraph('NVIDIA TTM税前权益投资收益约305.52亿美元，当前TTM净利不能全视作芯片重复经营所得；VRT预付款支持CFO，未来需履约。NVDA现金224.43亿美元、可交易债务证券341.43亿美元和权益证券427.83亿美元必须分列，权益证券不是无风险现金；债务333.66亿美元已含流动部分，不能重复加。')+c('NVDA27Q2','VRT26Q2')+table(['反向条件演算','第3年所需EPS USD','较当前4季EPS所需年增速','分析师假设'],reverse)+note('这是透明的价格条件测算，不是预测或目标价。末期25倍和10%仅为演示假设，不能证明这些公司应享有同倍数；若投资收益消失、股份稀释或现金转换恶化，所需可持续经营增长可能更高。未取得合规一致预期，不能称高于/低于市场预期。')))
 C,r,n=D(50000),D('.10'),3;crf=r*(1+r)**n/((1+r)**n-1);energy=D('1.2')*D('1.2')*8760*D('.08');annual=C*crf+C*D('.03')+energy
 unitrows=[]
 for u in [D('.4'),D('.6'),D('.8')]:
  hours=8760*u;unitrows.append([pct(u),fmt(hours,0),fmt(annual/hours),fmt(D(4)*hours-annual)])
 sec.append(section('economics','底层经济账：利用率、技术替换和合格任务',paragraph('以下全部是分析师假设，用于展示机制，不是任何公司的真实租价或采购合同。每GPU分摊安装资本5万美元、经济寿命3年、残值0、资本成本10%；年维护为原始资本3%；分摊IT功率1.2kW、PUE1.2、电价0.08美元/kWh，简化为持续满电负载。')+'<div class="formula">资本回收因子 CRF = r(1+r)^n / [(1+r)^n−1]<br>年经济总成本 = 安装资本 × CRF + 固定维护 + 用电<br>每可计费小时成本 = 年经济总成本 / (8760 × 付费利用率)</div>'+paragraph(f'本例年总经济成本为{fmt(annual)}美元；假设实现租价4美元/小时，覆盖该成本需要计费利用率约{pct(annual/(8760*D(4)))}。')+table(['付费利用率','年计费小时','经济成本 USD/小时','4美元租价下年经济剩余 USD'],unitrows)+paragraph(f'60%利用率时，电价翻倍使成本增加约{fmt(energy/(8760*D(".6")),3)}美元/小时；利用率下滑或设备寿命缩短可能更猛烈。但无法供电会阻断全部收入，不能由电费占比推断电力不重要。租赁服务器应选择一致的资本/租赁口径；本例资本年金已经包含资本成本，不能再把同一资产利息和本金重复加成经营成本。之后另做实际CapEx、债务本息、租赁、税与稀释到普通股现金的桥。')+table(['模型降价条件 / 假设单位','收费','变动成本','单位贡献 / 含义'],[
 ['起点','1.00','0.70','0.30；未计训练/研发/销售'],['效率改善足够','0.50','0.14','0.36；单价下降但贡献增加'],['竞争快于成本下降','0.30','0.42','−0.12；调用增长可能扩大损失']])+paragraph('成本降低可以催生更多需求，也可以被竞争和客户拿走。要补模型大小/上下文、重试、缓存、输入输出、模型路由和人工复核，按客户接受的合格任务计价；token更便宜并不自动等于持久高利润。')))
 sec.append(section('financing','资本循环与脆弱点：现金不能重复计算','<div class="flow">外部客户预算 → 应用/模型收入 → 云采购 → GPU/设备/园区支出 → 电力和供应链<br>↑ 模型股权融资/云投资/供应商投资 → 承诺采购和预付款 → ↑ 部分云订单与芯片收入</div>'+paragraph('这是需要核验的资金链，不是造假结论。同一笔资金可能先被记为股权融资，再成为云订单和芯片收入；把这些加总会夸大最终需求。反过来，跨投资也不证明没有独立客户、真实服务或现金回收。应逐合同区分已到账现金、未提款融资、采购承诺、客户预付、可取消预约、当期收入和已收款。')+table(['脆弱节点','当前财务锚点','最先失效的机制'],[
 ['CoreWeave / 新云','H1 CFO36.63−现金PPE/软件141.17=−104.54亿美元；净融资139.85亿美元。Q2 GAAP经营亏损0.49亿美元，净利息6.40亿美元','付费利用率/租价下降→现金缺口→设备抵押价值/契约→再融资/稀释。调整EBITDA15.10亿美元不能替代偿债现金。'],
 ['客户集中与积压','CRWV Q2前三大客户占36%/26%/10%；积压1,040亿美元有条件','模型客户融资/上线延迟可传到云收款，再传供应链。积压不等于已赚取和收现。'],
 ['租赁和未开工承诺','CRWV债务350.68亿美元，运营租赁现值163.19亿美元；未开始租赁355亿美元为未折现承诺','不同日期、现值与未折现口径不能简单相加称当日净债务；DCF履约成本与EV索偿不能重复扣。'],
 ['股权市场融资','GOOG Q2普通股发行净额304.99亿美元、强制转换优先股190.63亿美元；ATM授权须另分','应按原披露：ATM授权为400亿美元且截至6/30尚无发行；授权不是到账现金。融资使建设可持续但有优先权/稀释成本。'],
 ['智谱/国内应用融资','智谱2027美元结算CB与亏损；讯飞9M负现金投入差额、依赖定增/其他融资','融资窗口收紧时，经营增长与普通股价值可背离；逐项到期安排比“账上钱多”更有用。']])+c('CRWV26Q2','CRWV26Q2FILING','goog-q2','zai-financing-complete','iflytek-q3')+paragraph('最重要的联合压力不是独立事件相加：电力延期→服务器闲置→客户付款/上架延期→云债务和租约照付→模型融资依赖上升→供应商订单/预付款逆转。全产业链持仓可能共享同一个客户预算与融资因子，不能当自然分散。历史资本密集行业提供压力机制的参照，但不支持给本次黑天鹅编造概率或断言必然重演。')))
 sec.append(section('institutional','与公开机构研究交叉验证',table(['公开参考','其范围与判断','本稿如何使用'],[
 ['IEA / 4月更新','物理能源预测：2030年全体DC约950TWh','约束总量叙事，回到地区供电/时点/合同；不由用电增长直接推出发电股回报'],
 ['Goldman Sachs / 10月19日','估计2026—2031整个AI建设约7.6万亿美元，涉及算力、DC、电力','考察融资和瓶颈；是预测且存在业务利益，不当已经花掉或最终客户需求'],
 ['Morgan Stanley Institute / 3月9日','估计2025—2028 DC建设融资2.9万亿美元：1.4万亿云厂现金、0.2万亿公司债、0.15万亿证券化、0.8万亿私贷/JV、0.35万亿其他','范围/期间与GS不同，不相加、不平均或称一致预期。页面说明不是正式FINRA研究报告'],
 ['巴菲特/芒格等方法原则','所有者收益、能力圈、资本配置、逆向思考与价格约束','应用方法，不冒称大师会买这些证券：现金/必要再投资→融资后普通股回报；主动找最强反证']])+c('IEA26','GS26','MS26')+paragraph('本轮交叉验证形成的修正包括：保留BYD Q2恢复和真实云经营利润，纠正将税前投资收益直接从税后利润相减、将普通股分子等同合并净利，以及将预约/积压/预付当收入。研究质量应通过新证据能否推翻结论衡量，不能以网页完整、测试通过或模型自信程度代替投资效果。')))
 sec.append(section('monitor','仪表盘、事件传导与更新规则',table(['频率/信息源','重点数据','触发后的研究动作'],[
 ['每日 / 交易所公告、公司IR、监管原文','新融资/回购/CB、客户合同变化、出口限制、园区许可/停电、业绩日期','先确认发布日期、对象和生效日，再映射收入/成本/CapEx/资金桥；价格波动本身只触发查因'],
 ['每周 / 公司与项目原始材料','可用/已通电容量、设备交期、GPU租赁实现价、融资利差','未取得可靠同口径GPU价格/利用率时保留缺口，不用网站广告报价当已成交均价'],
 ['季度 / SEC、HKEX、CNINFO、现金表','收入/经营利润、应收/预付/递延、现金PPE/租赁、SBC/股份、客户集中','收入增长而现金/普通股利润背离→拆营运资本/投资收益/资本化；两个连续期间同口径恶化再重做基准情景'],
 ['高优先级 / 可核实事件','债务契约/偿付风险、重大订单取消、实际停电/网络安全事故、关键禁运','即刻补证并冻结旧结论有效性；先量化现金和持续经营影响，不靠泛化情绪给目标价'],
 ['宏观 / 美联储与资本市场','9/16政策区间3.75%—4.00%；10/27—28FOMC已安排','利率/信用利差→融资成本与折现率；长约负债和远期盈利更敏感，未来会议结果未知'],
 ['下一财报窗口 / 公司官方日历','10/28 VRT与NOW、10/29 Amazon；BYD10/29见独立报告','比较披露的收入/利润/现金/订单质量与旧假设，不能把预定结果写成事实']])+c('FED26','FEDCAL','VRT26Q3DATE','now-calendar','AMZCAL')+table(['待补证类型','内容','对结论的限制'],[
 ['原文存在但尚未勾稽','全量租赁、预付、维持CapEx、投资税项、SBC与完全稀释资本表','不能给完整EV或同口径估值排名'],['未获得公开可靠数据','私人模型审计现金流、GPU实际成交价/利用率、独立客户ROI','单位经济性只作条件测算，不给目标价/资金跑道'],['因果机制尚不确定','效率下降价与需求弹性、模型与应用议价权、硬件经济寿命','保持竞争情景，不给虚构概率'],['未来结果未到','长约通电、2027偿债、下一季度盈利与现金','用新版本记录证实/证伪，当前不声称预测成功']])+paragraph('置信度采用可解释分层：已列原文选定事实与算术较高；利润传导/护城河归因中等；未来估值、私募普通股回报和尾部事件概率较低或不可判断。这里没有经过历史回测校准的胜率百分比。')))
 rows=[]
 for m in market['rows']:
  if m['status']!='observed':continue
  day=(D(m['price'])/D(m['prior_price'])-1)*100
  rows.append([E(m['symbol']),E(m['name']),E(m['currency']),fmt(m['price']),E(m['observation_date']),fmt(day)+'%',ref(m['source_page'],'Yahoo')])
 sec.append(section('prices','40个标的价格快照与覆盖边界','<label for="price-filter">检索公司或代码</label><br><input id="price-filter" class="filter" data-filter-table="prices-table" placeholder="例如 NVDA、比亚迪、海光">'+'<div id="prices-table">'+table(['代码','公司','币种','参考价','当地日期','较上日','来源'],rows)+'</div>'+paragraph('这是一张价格索引，不是40家公司完整推荐榜。Yahoo公开日线40/40返回观察值，日期均为10/23；美国21个标的另尝试Alpaca免费IEX交叉检查。IEX不代表全市场，部分盘口为零/异常，本稿丢弃全部bid/ask，不以此推断流动性。行情下载成功只证明本次取得资料，不保证实时性、可用性、复权历史或交易执行价格。价格不一致时应先核交易时区、市场和调整口径。')))
 result=page('AI全栈：从电力到应用的资本与回报','八层产业地图、真实盈利、现金建设、私募与上市融资、价格条件和风险传导。','各层已经分化：真实经营利润与资金缺口同时存在','研究重心是外部客户现金如何穿透资本开支、融资和稀释成为普通股回报；行业增长不能替代证券价格判断。',[('产业链覆盖','8 层','能源、电网→模型→应用'),('行情索引','40 个','10/23日线；非实时'),('IEA 2030用电','950 TWh','全体数据中心预测，非纯AI'),('本轮估值诊断','4 家','TTM与反向条件；无目标价')],sec,sources,'ai-full-stack.html')
 (OUT/'unit-economic-diagnostics.json').write_text(json.dumps(dict(classification='illustrative_assumptions_not_company_forecast',gpu=dict(installed_capital='50000',life_years=3,salvage='0',capital_cost='0.1',maintenance_rate='0.03',it_kw='1.2',pue='1.2',usd_kwh='0.08',fixed_full_power_load=True,capital_recovery_factor=str(crf),annual_cost=str(annual),rent_usd_hour='4',breakeven_paid_utilization=str(annual/(8760*D(4)))),not_included=['tax','working_capital','network_software_and_staff_not_captured_by_allocated_installation_and_maintenance','actual_debt_cash_schedule'],limitation='Economic annuity includes capital cost; do not add the same capital interest/principal again. This is not levered common equity cash flow.'),ensure_ascii=False,indent=2)+'\n')
 return result,diagnostics

def portable(value):
 if isinstance(value,dict):return {k:portable(v) for k,v in value.items() if k not in {'raw_path','archive_manifest_file'} and not k.endswith('_local_path')}
 if isinstance(value,list):return [portable(v) for v in value]
 if isinstance(value,str):return value.replace(str(ROOT)+'/','')
 return value

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 source=ROOT/'data/research/2026-10-25'
 names=['byd-agent.json','ai-infra-agent.json','ai-apps-agent.json','infra-valuation-inputs.json','adversarial-review.json']
 for name in names:
  if (source/name).exists():
   value=json.loads((source/name).read_text())
   if name=='ai-apps-agent.json':
    for s in value['sources']:
     if s['id']=='pltr-q2':
      s['prior_attempt']={k:s[k] for k in ('url','retrieval_status','sha256','bytes') if k in s}
      for k in ('raw_path','sha256','bytes','mime','final_url'):s.pop(k,None)
      s.update(url='https://www.sec.gov/Archives/edgar/data/1321655/000132165526000039/a2026q2ex991pressrelease.htm',retrieval_status='official_SEC_body_read_via_web',body_reviewed=True,notes='根研究者补读正式附件；保留原IR脚本壳失败记录。')
   (OUT/name).write_text(json.dumps(portable(value),ensure_ascii=False,indent=2)+'\n')
 b=read('research/2026-10-25/byd-agent.json');infra=read('research/2026-10-25/ai-infra-agent.json');apps=read('research/2026-10-25/ai-apps-agent.json')
 byd=build_byd(b);ai,diags=build_ai(infra,apps,read('research/2026-10-25/infra-valuation-inputs.json'),read('research/2026-10-25/market-snapshot.json'))
 (OUT/'valuation-diagnostics.json').write_text(json.dumps(diags,ensure_ascii=False,indent=2)+'\n')
 publications=[dict(id='byd-2026-10-25',title='比亚迪：恢复、现金与A/H定价',company_id='byd',description='季度恢复、研发与汇兑、现金与融资、海外政策、A/H价格条件及反方审查。',route='/research/byd-2026-10-25.html',**byd),dict(id='ai-2026-10-25',title='AI全栈：从电力到应用的资本与回报',company_id=None,description='八层产业、全球上市与私募资本、现金循环、单位经济性及40标的价格索引。',route='/research/ai-2026-10-25.html',**ai)]
 catalog=dict(as_of='2026-10-25',price_as_of='2026-10-23',version=1,investment_ready=False,publications=publications)
 (ROOT/'knowledge/research-publications.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'reports':publications,'investment_ready':False},ensure_ascii=False))

if __name__=='__main__':main()
