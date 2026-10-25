"""Transparent research triggers, not trade signals or estimated probabilities."""
from datetime import date
from .models import number, cumulative_quarter


def observations(facts):
    alerts = []
    # A 50% CFO decline is an explicit, uncalibrated research-screen threshold.
    # Do not mix flow and instant values, consolidated and parent, or periods.
    flows = [f for f in facts if f["metric"] == "operating_cash_flow" and f.get("period_start")]
    quarters = []
    for current in flows:
        end = date.fromisoformat(current["period_end"])
        if end.month != 9 or end.day != 30 or current["period_start"][5:] != "01-01":
            continue
        previous = [f for f in flows if f["period_end"] == f"{end.year}-06-30"
                    and all(f.get(k) == current.get(k) for k in ("unit", "currency", "scope", "basis", "period_start"))]
        if previous:
            q = dict(current, value=cumulative_quarter(current, previous[-1]),
                     period_start=f"{end.year}-07-01", input_ids=[current["id"], previous[-1]["id"]])
            quarters.append(q)
    for current in quarters:
        prior = [q for q in quarters if int(q["period_end"][:4]) == int(current["period_end"][:4])-1
                 and all(q.get(k) == current.get(k) for k in ("unit", "currency", "scope", "basis"))]
        if not prior or number(prior[-1]["value"]) <= 0:
            continue
        change = number(current["value"])/number(prior[-1]["value"])-1
        if change <= number("-0.5"):
            alerts.append(dict(key="quarter_cfo:"+current["period_end"], title="单季经营现金流显著下降，累计值掩盖变化",
                               severity="high", metric="operating_cash_flow", current=current["value"],
                               prior=prior[-1]["value"], change=str(change), period_end=current["period_end"],
                               fact_ids=current["input_ids"]+prior[-1]["input_ids"],
                               mechanism="累计现金流转单季 → 核查营运资金与回款 → 重估现金收益和投入能力；不能仅据此断言需求永久受损。",
                               next_source="现金流附注、应收/库存/预付款、管理层解释及下一期回款",
                               rule="单季CFO同比≤−50%，未校准的研究筛查阈值，不是卖出规则"))
    reported = [f for f in facts if f["metric"] == "reported_fcf" and number(f["value"]) < 0]
    adjusted = [f for f in facts if f["metric"] == "adjusted_fcf_ex_compute_prepayment"]
    for f in reported:
        others = [a for a in adjusted if all(a.get(k) == f.get(k) for k in (
            "period_start", "period_end", "unit", "currency", "scope")) and number(a["value"]) > 0]
        if others:
            alerts.append(dict(key="fcf_adjustment:"+f["period_end"], title="报告自由现金流与调整后指标方向不同",
                               severity="high", fact_ids=[f["id"], others[-1]["id"]],
                               mechanism="排除算力预付款使指标转正，但现金付款仍已发生；需核查预付款资产、履约和未来投入。",
                               next_source="公司现金流定义、预付款及资本承诺、后续履约与回报",
                               rule="同期间报告FCF<0且排除预付款后FCF>0；定义差异核查规则"))
    return alerts
