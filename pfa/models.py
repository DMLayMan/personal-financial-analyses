"""Deterministic valuation scenarios. These are assumptions, never price targets."""
from decimal import Decimal, InvalidOperation, localcontext


def number(value, name="数值"):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(name + "必须是十进制数") from None
    if not result.is_finite() or abs(result) > Decimal("1e24"):
        raise ValueError(name + "不是有效的有限数值")
    return result


def bounded(data, key, low, high):
    n = number(data[key], key)
    if not number(low) <= n <= number(high):
        raise ValueError(key + "超出允许范围")
    return n


def serial(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, list):
        return [serial(v) for v in value]
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    return value


def earnings_scenario(revenue, margin, assumptions):
    """Five-year distributable-earnings illustration; no FCFE equivalence claimed.

    The payout is an explicit scenario, not an assertion of cash available.
    Total common equity in reporting currency, not a per-security target.
    """
    with localcontext() as ctx:
        ctx.prec = 34
        growth = bounded(assumptions, "growth", "-0.8", "1")
        change = bounded(assumptions, "margin_change", "-0.4", "0.4")
        terminal_pe = bounded(assumptions, "terminal_pe", "0", "100")
        discount = bounded(assumptions, "discount_rate", "0.01", "0.8")
        payout = bounded(assumptions, "payout", "0", "1")
        revenue, margin = number(revenue), number(margin)
        if revenue <= 0 or not 0 <= margin + change <= 1:
            raise ValueError("正收入和合理的净利率是该情景模型的适用条件")
        rows, pv_distributions = [], Decimal(0)
        for year in range(1, 6):
            sales = revenue * (1 + growth) ** year
            net_margin = margin + change * Decimal(year) / 5
            profit = sales * net_margin
            distribution = profit * payout
            present = distribution / (1 + discount) ** year
            pv_distributions += present
            rows.append(dict(year=year, revenue=sales, net_margin=net_margin,
                             net_income=profit, distribution=distribution,
                             pv_distribution=present))
        terminal_value = rows[-1]["net_income"] * terminal_pe
        pv_terminal = terminal_value / (1 + discount) ** 5
        return serial(dict(rows=rows, pv_distributions=pv_distributions,
                           pv_terminal=pv_terminal, total_equity=pv_distributions + pv_terminal,
                           terminal_share=pv_terminal / (pv_distributions + pv_terminal)
                           if pv_distributions + pv_terminal else None,
                           formula="Σ(NI_t × payout)/(1+Ke)^t + (NI_5 × PE_5)/(1+Ke)^5",
                           method="盈利与分配假设下的股权价值情景；非现金流DCF、非目标价"))


def bank_scenario(common_equity, assumptions):
    """Clean-surplus residual-income model, five years plus terminal growth.

    BV_t = BV_t-1 + NI_t - dividends_t; equity = BV0 + PV(residual income).
    OCI/capital changes and regulatory payout constraints need separate review.
    """
    with localcontext() as ctx:
        ctx.prec = 34
        bv = number(common_equity)
        if bv <= 0:
            raise ValueError("普通股权益必须为正")
        roe = bounded(assumptions, "roe", "-0.1", "0.4")
        cost = bounded(assumptions, "discount_rate", "0.01", "0.8")
        payout = bounded(assumptions, "payout", "0", "1")
        growth = bounded(assumptions, "terminal_growth", "-0.05", "0.08")
        if cost <= growth:
            raise ValueError("股权成本必须高于终值增长率")
        opening, pv_ri, rows = bv, Decimal(0), []
        for year in range(1, 6):
            profit = bv * roe
            ri = profit - bv * cost
            dividends = profit * payout
            end = bv + profit - dividends
            if end <= 0:
                raise ValueError("普通股权益耗尽，需要困境处置模型")
            pv_ri += ri / (1 + cost) ** year
            rows.append(dict(year=year, opening_equity=bv, net_income=profit,
                             dividend=dividends, residual_income=ri, closing_equity=end))
            bv = end
        # Terminal clean-surplus payout must equal 1 - g/ROE; it is not the year-5 payout.
        if roe <= 0 or not 0 <= growth / roe <= 1:
            raise ValueError("终值增长必须能由正ROE和合理留存支持")
        terminal_ri = bv * (roe - cost)
        terminal_pv = terminal_ri / (cost - growth) / (1 + cost) ** 5
        return serial(dict(rows=rows, opening_equity=opening, pv_residual_income=pv_ri,
                           pv_terminal_residual=terminal_pv,
                           total_equity=opening + pv_ri + terminal_pv,
                           terminal_payout=1-growth/roe,
                           formula="BV0 + Σ[(ROE−Ke) × BV_(t−1)]/(1+Ke)^t + RI6/(Ke−g)/(1+Ke)^5",
                           method="银行普通股剩余收益情景；含净盈余、资本与终值假设"))


def cumulative_quarter(current, previous):
    keys = ("metric", "currency", "unit", "scope", "basis", "period_start")
    if any(current.get(k) != previous.get(k) for k in keys):
        raise ValueError("累计值的期间、单位、币种、范围或口径不一致")
    if current["period_end"] <= previous["period_end"]:
        raise ValueError("累计期末必须递增")
    return format(number(current["value"]) - number(previous["value"]), "f")
