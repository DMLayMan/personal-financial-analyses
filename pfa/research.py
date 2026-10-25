"""Evidence checks, follow-up planning, models and append-only conclusions.

No external LLM is configured. Hypotheses are analyst inputs; rules constrain
their use and never label a fluent narrative as a verified investment thesis.
"""
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from .models import number, serial, earnings_scenario, bank_scenario, cumulative_quarter
from .store import Store, digest, now, uid, dump
from .monitoring import observations
from .assurance import RUNNING_KERNEL, ACTUAL_LABELS, EVIDENCE_LABELS, integrity, temporal_actual, comparable_period
from . import __version__


class Conflict(ValueError):
    pass


LABELS = {
    "revenue": "营业收入", "net_income": "归属净利润（见原始定义）",
    "net_income_common": "普通股股东净利润", "operating_profit": "营业利润",
    "operating_cash_flow": "经营现金流", "capex_cash": "现金资本投入",
    "cash": "现金（见原始定义）", "debt": "债务（见覆盖范围）",
    "shares_diluted": "期间平均稀释股数", "shares_outstanding": "期末实际股数",
    "eps": "每股收益", "common_equity": "普通股权益", "equity": "股东权益",
    "nim": "净利息收益率", "net_interest_income": "净利息收入",
    "credit_cost": "信用成本", "roe": "普通股回报率（见期间）", "bvps": "普通股每股净资产",
    "share_based_compensation": "股份支付", "free_cash_flow_reported": "公司定义自由现金流",
    "earnings_for_eps": "每股收益勾稽利润分子（见调整定义）",
}


def annual(fact):
    try:
        days = (date.fromisoformat(fact["period_end"]) -
                date.fromisoformat(fact["period_start"])).days
        return 330 <= days <= 380
    except (KeyError, TypeError, ValueError):
        return False


def fact_key(fact):
    return tuple(fact.get(k, "") for k in (
        "metric", "period_start", "period_end", "unit", "currency", "scope", "basis"))


class Research:
    def __init__(self, store):
        self.store = store

    def issuer(self, db, ident):
        item = self.store.get(db, ident)
        if item["kind"] != "issuer":
            raise ValueError("公司不存在")
        return item

    def seed(self, path="fixtures/companies.json"):
        package = json.loads(Path(path).read_text())
        with self.store.tx() as db:
            for company in package["companies"]:
                ident = company["id"]
                if db.execute("SELECT 1 FROM records WHERE id=?", (ident,)).fetchone():
                    continue
                config = {k: v for k, v in company.items() if k not in ("id", "documents")}
                self.store.add(db, "issuer", ident, config, ident)
                for doc in company.get("documents", []):
                    self.import_document(db, ident, doc, doc.get("facts", []), curated=True)
                self.store.log(db, ident, "建立研究档案", {"source": "公开原文局部取证包", "version": package.get("version")})

    def import_document(self, db, issuer, document, facts=(), curated=False):
        self.issuer(db, issuer)
        if not document.get("url", "").startswith("https://"):
            raise ValueError("来源必须保留HTTPS原文链接")
        if not document.get("sha256") or not document.get("retrieved_at"):
            raise ValueError("资料需要校验值与实际取得时间")
        for prior in self.store.list(db, "document", issuer):
            if prior.get("sha256") == document["sha256"] and prior["url"] == document["url"]:
                return prior
        data = {k: v for k, v in document.items() if k not in ("facts", "id", "kind", "issuer", "created_at")}
        data["original_id"] = document.get("id")
        data["capabilities"] = dict(read=True, continuous=False, point_in_time=False,
                                    public_redistribution="未核实，当前仅本地研究")
        item = self.store.add(db, "document", issuer, data)
        for value in facts:
            row = self.add_fact(db, issuer, dict(value, document_id=item["id"]))
            if curated and value.get("verification_status") in ("verified_source_tied", "verified", "source_tied"):
                self.check_fact(db, issuer, row["id"], "verified", value.get("note") or "本次研究者与原始财务表逐项核对", "analyst_seed")
        self.store.log(db, issuer, "导入资料版本", {"document_id": item["id"], "sha256": data["sha256"], "facts": len(facts)})
        return item

    def add_fact(self, db, issuer, data):
        doc = self.store.get(db, data["document_id"])
        if doc["kind"] != "document" or doc["issuer"] != issuer:
            raise ValueError("事实与来源公司不一致")
        for key in ("metric", "value", "unit", "period_end", "scope", "basis", "locator", "quote"):
            if key not in data or data[key] in (None, ""):
                raise ValueError("事实缺少字段：" + key)
        date.fromisoformat(data["period_end"])
        if data.get("period_start"):
            date.fromisoformat(data["period_start"])
            if data["period_start"] > data["period_end"]:
                raise ValueError("期间起点晚于终点")
        value = format(number(data["value"]), "f")
        currency = data.get("currency") or doc.get("currency")
        money_metrics = {"revenue", "net_income", "net_income_common", "earnings_for_eps", "operating_cash_flow", "capex_cash", "common_equity", "cash", "debt", "equity", "operating_profit", "net_interest_income"}
        if data["metric"] in money_metrics and data["unit"] != currency:
            raise ValueError("金额必须换算为所标币种的元单位；不能把千元、比率或股数作为金额输入")
        if data["metric"] in {"nim","credit_cost","roe","cet1","npl_ratio"} and data["unit"] != "ratio":
            raise ValueError("比率使用小数ratio单位，例如1.83%应记录为0.0183")
        payload = {k: v for k, v in data.items() if k not in ("id", "kind", "issuer", "created_at", "verification_status")}
        payload.update(value=value, currency=currency,
                       evidence_label=data.get("evidence_label", "fact_source_reported"))
        if payload["evidence_label"] not in EVIDENCE_LABELS:
            raise ValueError("未知证据类型；必须区分已报实际、管理层说法、预测与假设")
        payload["period_start"] = data.get("period_start") or None
        item = self.store.add(db, "fact", issuer, payload)
        self.store.log(db, issuer, "提取候选事实", {"fact_id": item["id"], "metric": data["metric"]})
        return item

    def check_fact(self, db, issuer, fact_id, status, reason, actor="local_user"):
        fact = self.store.get(db, fact_id)
        if fact["kind"] != "fact" or fact["issuer"] != issuer:
            raise ValueError("事实不存在或不属于该公司")
        if status not in ("verified", "rejected", "candidate") or len(reason.strip()) < 6:
            raise ValueError("请提供核验结果及至少六个字符的核验理由")
        self.store.add(db, "fact_check", issuer, dict(fact_id=fact_id, status=status, reason=reason, actor=actor))
        self.store.log(db, issuer, "事实核验变更", dict(fact_id=fact_id, status=status, reason=reason))

    def facts(self, db, issuer):
        checks = {}
        for check in self.store.list(db, "fact_check", issuer):
            checks[check["fact_id"]] = check
        docs = {d["id"]: d for d in self.store.list(db, "document", issuer)}
        out = []
        for fact in self.store.list(db, "fact", issuer):
            check = checks.get(fact["id"], {})
            out.append(dict(fact, status=check.get("status", "candidate"), check=check,
                            label=LABELS.get(fact["metric"], fact["metric"]),
                            source=docs[fact["document_id"]]))
        return out

    def fingerprint(self, db, issuer):
        kinds = ("issuer", "document", "fact", "fact_check", "event", "hypothesis", "gap_resolution")
        records = {kind: self.store.list(db, kind, issuer) for kind in kinds}
        records["running_kernel"] = RUNNING_KERNEL
        records["source_integrity"] = [(d["id"], integrity(d)) for d in records["document"]]
        return digest(records)

    def expect(self, db, issuer, expected):
        if expected is None or self.store.revision(db, issuer) != int(expected):
            raise Conflict("研究已更新，请刷新后重试；不会覆盖新记录")

    def current_hypothesis(self, db, issuer):
        latest = self.store.list(db, "hypothesis", issuer)
        if latest:
            return latest[-1]
        company = self.issuer(db, issuer)
        return {k: company.get(k, "") for k in ("question", "thesis", "counter_thesis", "transmission")}

    def quality(self, db, issuer):
        company = self.issuer(db, issuer)
        facts = self.facts(db, issuer)
        documents = self.store.list(db, "document", issuer)
        source_integrity = {d["id"]: integrity(d) for d in documents}
        groups = defaultdict(list)
        for fact in facts:
            if fact["status"] == "verified" and fact.get("evidence_label") in ACTUAL_LABELS:
                groups[fact_key(fact)].append(fact)
        conflicts = [dict(key=list(key), facts=[f["id"] for f in values],
                          metric=key[0], detail="同期间同口径存在不同值，不能自动选新值或平均")
                     for key, values in groups.items() if len({number(f["value"]) for f in values}) > 1]
        conflicted = {ident for c in conflicts for ident in c["facts"]}
        usable = [f for f in facts if f["status"] == "verified" and f["id"] not in conflicted
                  and f.get("scope") == "consolidated" and f.get("currency") == company["currency"]
                  and source_integrity.get(f["document_id"]) == "matched" and temporal_actual(f)]
        # Stable published-time ordering; no synthetic averaging or latest-filed period guessing.
        usable.sort(key=lambda f: (f["period_end"], f["source"].get("published_at") or "", f["created_at"]))
        gaps = []
        def gap(key, title, why, priority="high", source="公司原始报告及附注", blocks="explanation", **extra):
            gaps.append(dict(key=key, title=title, why=why, priority=priority,
                             next_source=source, blocks=blocks, **extra))
        for document in documents:
            state = source_integrity[document["id"]]
            if state != "matched":
                gap("integrity:"+document["id"], "原件不可复核："+document["title"],
                    "原件缺失、超出来源目录或校验值不匹配；相应条目已排除，需重新取证。状态："+state,
                    source=document["url"], blocks="evidence")
        for conflict in conflicts:
            gap("conflict:" + digest(conflict["key"])[:12], "解决数字冲突：" + LABELS.get(conflict["metric"], conflict["metric"]),
                conflict["detail"], blocks="model", fact_ids=conflict["facts"])
        for planned in company.get("missing_evidence", []):
            gap(planned["key"], planned["title"], planned["why"], planned.get("priority", "high"),
                planned.get("next_source", "公司原文"), planned.get("blocks", "explanation"),
                target_url=planned.get("target_url"))
        for event in self.store.list(db, "event", issuer):
            gap("event:"+event["id"], "事件传导待验证："+event["title"],
                event["mechanism"]+"；关键未知："+event["unknown"],
                source=event["source_url"]+"；"+event["next_validation"], blocks="explanation")
        if company.get("sector") == "bank" and not any(f["metric"] == "common_equity" for f in usable):
            gap("required_common_equity", "补齐合并普通股权益", "普通股权益缺失会阻止银行剩余收益估值；不以全部权益代替。", blocks="model")
        if company.get("sector") != "bank" and not any(f["metric"] == "revenue" and annual(f) for f in usable):
            gap("required_annual_revenue", "补齐同口径年度盈利基线", "中期披露不能直接乘二；需要合并年度收入和归属利润。", blocks="model")
        monitors = observations([f for f in usable if f.get("evidence_label") in ACTUAL_LABELS
                                 or f["metric"] in ("reported_fcf", "adjusted_fcf_ex_compute_prepayment")])
        for monitor in monitors:
            gap(monitor["key"], monitor["title"], monitor["mechanism"], source=monitor["next_source"],
                blocks="cash_return", fact_ids=monitor["fact_ids"], rule=monitor["rule"])
        rejected = [f for f in facts if f["status"] == "rejected"]
        if rejected:
            gap("rejected_facts", "被撤回事实的替代依据", "事实核验已撤回；旧模型和结论需重算复核", blocks="evidence")
        candidates = [f for f in facts if f["status"] == "candidate"]
        if candidates:
            gap("candidates", "核验新增提取候选", "新资料尚未被接纳为模型输入，不因抓取成功自动核验", blocks="evidence")
        resolutions = {r["gap_key"]: r for r in self.store.list(db, "gap_resolution", issuer)}
        for item in gaps:
            resolution = resolutions.get(item["key"])
            # Accepting an unknown never erases the gap or upgrades its evidence quality.
            item["handling"] = resolution
            item["state"] = "已记录处理，限制仍保留" if resolution else "待补证"
            if resolution and resolution.get("disposition") == "resolved":
                item["resolved"] = False
                item["state"] = "补证回应待相关性与充分性审查；引用条目不能自动关闭经营未知"
            item["decision_impact"] = {
                "model": "可能改变模型能否运行或价值范围，优先核查。",
                "cash_return": "可能改变现金回报与融资韧性判断，不能仅看利润。",
                "evidence": "可能推翻输入事实，限制受影响判断。",
            }.get(item["blocks"], "可能改变经营解释或证券结论，需要区分性证据。")
            item["stop_rule"] = "取得能区分解释的证据后复核；资料不可得则接受未知并限制相应结论，不无限重复搜索。"
        gaps.sort(key=lambda g: ({"model":0,"cash_return":1,"evidence":2}.get(g["blocks"],3), g["priority"] != "high"))
        active_gaps = [g for g in gaps if not g.get("resolved")]
        resolved_gaps = [g for g in gaps if g.get("resolved")]
        return dict(facts=facts, usable=usable, conflicts=conflicts, gaps=active_gaps, resolved_gaps=resolved_gaps, monitors=monitors,
                    source_integrity=source_integrity,
                    verified=sum(f["status"] == "verified" for f in facts),
                    candidates=len(candidates), rejected=len(rejected))

    def defaults(self, company):
        if company.get("sector") == "bank":
            return {"downside": {"roe": "0.09", "discount_rate": "0.14", "payout": "0.3", "terminal_growth": "0.01"},
                    "base": {"roe": "0.12", "discount_rate": "0.12", "payout": "0.35", "terminal_growth": "0.02"},
                    "upside": {"roe": "0.14", "discount_rate": "0.11", "payout": "0.4", "terminal_growth": "0.025"}}
        return {"downside": {"growth": "-0.02", "margin_change": "-0.01", "terminal_pe": "10", "discount_rate": "0.14", "payout": "0.2"},
                "base": {"growth": "0.05", "margin_change": "0", "terminal_pe": "18", "discount_rate": "0.12", "payout": "0.3"},
                "upside": {"growth": "0.10", "margin_change": "0.01", "terminal_pe": "25", "discount_rate": "0.10", "payout": "0.4"}}

    def build_model(self, db, issuer, assumptions=None, rationale="", confirmed=False):
        if not isinstance(confirmed, bool):
            raise ValueError("假设审议状态必须是明确布尔值")
        company = self.issuer(db, issuer)
        quality = self.quality(db, issuer)
        facts = [f for f in quality["usable"] if f.get("evidence_label") in ACTUAL_LABELS]
        bank = company.get("sector") == "bank"
        warnings = ["情景参数是研究假设，未从历史表现推导出未来成功概率。",
                    "未接入可靠现价、证券币种换算与市场共识；不能判断现价吸引力。",
                    "经营、融资和估值可能同时恶化；下行情景不是最大损失上限，也未验证黑天鹅预测能力。"]
        inputs, issues, scenarios, checks = [], [], {}, []
        selected = {}
        if bank:
            equities = [f for f in facts if f["metric"] == "common_equity"]
            if equities:
                selected["common_equity"] = equities[-1]
            else:
                issues.append("缺少已核验合并普通股权益，银行剩余收益估值暂缓；不使用全部归母权益代替")
        else:
            revenues = [f for f in facts if f["metric"] == "revenue" and annual(f)]
            pairs = []
            for revenue in revenues:
                profits = [f for f in facts if f["metric"] == "net_income"
                           and all(f.get(k) == revenue.get(k) for k in (
                               "period_start", "period_end", "currency", "scope", "basis"))]
                if profits:
                    pairs.append((revenue, profits[-1]))
            if pairs:
                revenue, profit = pairs[-1]
                selected.update(revenue=revenue, net_income=profit)
                adjusted = [f for f in facts if f["metric"] in ("net_income_common", "earnings_for_eps")
                            and all(f.get(k) == revenue.get(k) for k in (
                                "period_start", "period_end", "currency", "scope", "basis"))]
                selected["valuation_earnings"] = adjusted[-1] if adjusted else profit
                if adjusted:
                    warnings.append("估值盈利分子使用单独核验的普通股或EPS勾稽分子，区别于报告归母净利；稀释、限制性股票与其他权益调整按原文保留，仍非正常化利润。")
                # Income/cash bridge is diagnostic, not proof of distributable cash.
                for metric in ("operating_cash_flow", "capex_cash"):
                    same = [f for f in facts if f["metric"] == metric
                            and all(f.get(k) == revenue.get(k) for k in (
                                "period_start", "period_end", "currency", "scope", "basis"))]
                    if same:
                        selected[metric] = same[-1]
                prior = [p for p in pairs if comparable_period(revenue, p[0])]
                if prior:
                    selected.update(prior_revenue=prior[-1][0], prior_net_income=prior[-1][1])
            else:
                issues.append("缺少同期间、同币种、同合并口径的已核验年度收入和净利润；不将半年值乘二冒充年度")
            warnings += ["净利润作为盈利基线，正常化调整及永续债等权益归属需另核查。",
                         "分配比例不等于可分配现金，PE终值是情景假设，未完成独立估值复核。"]
        assumptions = assumptions if assumptions is not None else self.defaults(company)
        if set(assumptions) != {"downside", "base", "upside"}:
            raise ValueError("必须保留下行、基准、上行三个情景")
        if confirmed and len(rationale.strip()) < 12:
            raise ValueError("确认假设需至少十二字符的经营依据和适用边界")
        critical = {"common_equity"} if bank else {"revenue", "net_income", "net_income_common", "earnings_for_eps"}
        baseline_date = selected.get("common_equity", selected.get("revenue", {})).get("period_end", "")
        by_id = {f["id"]: f for f in quality["facts"]}
        for conflict in quality["conflicts"]:
            affected = [by_id[i] for i in conflict["facts"] if by_id[i]["metric"] in critical]
            if any(f["period_end"] >= baseline_date and (bank or annual(f)) for f in affected):
                issues.append("较新或当前基线有关键数字冲突，禁止回退旧年度替代；先解决冲突。")
        for fact in quality["facts"]:
            if (fact["metric"] in critical and fact["period_end"] >= baseline_date
                    and (bank or annual(fact)) and quality["source_integrity"].get(fact["document_id"]) != "matched"):
                issues.append("关键原件完整性未通过，禁止使用旧基线掩盖来源问题。")
                break
        if not issues:
            for key in ("downside", "base", "upside"):
                if bank:
                    scenarios[key] = bank_scenario(selected["common_equity"]["value"], assumptions[key])
                else:
                    rev, ni = number(selected["revenue"]["value"]), number(selected["valuation_earnings"]["value"])
                    scenarios[key] = earnings_scenario(rev, ni/rev, assumptions[key])
        diagnostics = {}
        # Recent interim facts update the diagnosis while annual scenarios retain a
        # disclosed annual base. A half-year is never silently annualized.
        if not bank:
            latest_revenues = [f for f in facts if f["metric"] == "revenue" and f.get("period_start")]
            comparable = [(current, prior) for current in latest_revenues for prior in latest_revenues
                          if comparable_period(current, prior)]
            if comparable:
                comparable.sort(key=lambda pair: (pair[0]["period_end"],
                    -(date.fromisoformat(pair[0]["period_end"])-date.fromisoformat(pair[0]["period_start"])).days))
                recent, prior = comparable[-1]
                comparison = [prior]
                selected["latest_revenue"] = recent
                if comparison and number(comparison[-1]["value"]) > 0:
                    selected["latest_comparative_revenue"] = comparison[-1]
                    diagnostics["latest_revenue_growth"] = number(recent["value"])/number(comparison[-1]["value"])-1
        else:
            for metric in ("nim", "credit_cost", "net_income", "net_interest_income", "cet1"):
                rows = [f for f in facts if f["metric"] == metric]
                if rows:
                    selected["latest_"+metric] = rows[-1]
                    diagnostics["latest_"+metric] = rows[-1]["value"]
        for key, fact in selected.items():
            inputs.append(dict(role=key, fact_id=fact["id"], value=fact["value"], currency=fact["currency"],
                               period_start=fact.get("period_start"), period_end=fact["period_end"],
                               source_id=fact["document_id"], locator=fact["locator"], basis=fact["basis"]))
        if not bank and "revenue" in selected:
            rev, ni = number(selected["revenue"]["value"]), number(selected["net_income"]["value"])
            diagnostics["net_margin"] = ni/rev if rev else None
            if "prior_revenue" in selected and number(selected["prior_revenue"]["value"]) > 0:
                diagnostics["revenue_growth"] = rev/number(selected["prior_revenue"]["value"])-1
                prior_ni = number(selected["prior_net_income"]["value"])
                diagnostics["net_income_growth"] = ni/prior_ni-1 if prior_ni > 0 else None
            if "operating_cash_flow" in selected:
                cfo = number(selected["operating_cash_flow"]["value"])
                diagnostics["cash_conversion"] = cfo/ni if ni > 0 else None
                if "capex_cash" in selected:
                    capex = number(selected["capex_cash"]["value"])
                    diagnostics["cfo_less_cash_capex"] = cfo-capex
                    diagnostics["cash_capex_to_cfo"] = capex/cfo if cfo > 0 else None
                    warnings.append("经营现金流减现金Capex只是算术桥，未涵盖全部租赁、内容支付、预付款和融资约束。")
            diagnostics["margin_100bp_profit_sensitivity"] = rev*number("0.01")
            checks.append(dict(name="年度与口径", result="通过", detail="收入与净利严格同期间同范围；未年度化中期数据"))
        elif bank and "common_equity" in selected:
            diagnostics["roe_100bp_profit_sensitivity"] = number(selected["common_equity"]["value"])*number("0.01")
            warnings += ["普通股利润、OCI、其他权益变动和资本分配限制需复核；不对银行使用企业自由现金流。"]
            checks.append(dict(name="银行普通股口径", result="通过", detail="使用普通股权益；仍需净盈余和资本约束审查"))
        if quality["conflicts"]:
            warnings.append("存在未解事实冲突，冲突值已排除；其他无冲突模型可继续，结论保持有条件。")
        model = dict(engine_version=__version__, kernel_digest=RUNNING_KERNEL, fingerprint=self.fingerprint(db, issuer),
                     baseline_as_of=selected.get("common_equity", selected.get("revenue", {})).get("period_end"),
                     currency=company["currency"], model_type="bank_residual_income" if bank else "earnings_scenario",
                     assumptions=assumptions, assumptions_confirmed=confirmed, rationale=rationale,
                     inputs=inputs, scenarios=scenarios, diagnostics=serial(diagnostics), checks=checks,
                     issues=issues, warnings=warnings,
                     support_assessment="illustrative_only", research_quality="not_validated",
                     status="blocked" if issues else "conditional" if not confirmed else "review_required")
        model["warnings"].append("情景折现起点为基线报告期末；尚未将已过去月份的实际与预测滚动衔接，不称为当前公允价值。")
        return self.store.add(db, "model_run", issuer, model)

    def review(self, db, issuer, data):
        runs = self.store.list(db, "model_run", issuer)
        if not runs or runs[-1]["fingerprint"] != self.fingerprint(db, issuer):
            raise ValueError("先在当前证据上运行模型，再进行反方审查")
        for key in ("strongest_counter", "response", "falsifier"):
            if len(data.get(key, "").strip()) < 12:
                raise ValueError("反方、回应和推翻条件各需至少十二字符")
        facts = {f["id"]: f for f in self.quality(db, issuer)["usable"]}
        refs = data.get("fact_ids", [])
        if not isinstance(refs, list) or not refs or any(i not in facts or facts[i]["status"] != "verified" for i in refs):
            raise ValueError("审查至少关联一条该公司的已核验事实")
        if data.get("verdict") not in ("conditional", "refuted", "supported"):
            raise ValueError("请明确审查结果")
        review = self.store.add(db, "review", issuer, dict(
            strongest_counter=data["strongest_counter"], response=data["response"],
            falsifier=data["falsifier"], verdict=data["verdict"], fact_ids=refs,
            run_id=runs[-1]["id"], fingerprint=self.fingerprint(db, issuer),
            reviewed_by=data.get("actor", "local_user"), independence="个人研究者的分步复核，非独立机构审查"))
        self.store.log(db, issuer, "反方审查", {"review_id": review["id"], "verdict": data["verdict"]})
        return review

    def publish(self, db, issuer, reason):
        if len(reason.strip()) < 12:
            raise ValueError("请说明本次形成或更新结论的理由，至少十二字符")
        runs, reviews = self.store.list(db, "model_run", issuer), self.store.list(db, "review", issuer)
        if not runs or not reviews:
            raise ValueError("需要模型运行与人工反方审查")
        run, review = runs[-1], reviews[-1]
        fingerprint = self.fingerprint(db, issuer)
        if run["fingerprint"] != fingerprint or review["fingerprint"] != fingerprint or review["run_id"] != run["id"]:
            raise Conflict("证据或模型已变化，先重算并重新审查，旧结论仍会保留")
        q = self.quality(db, issuer)
        prior = self.store.list(db, "conclusion", issuer)
        diagnostics = run["diagnostics"]
        growth = diagnostics.get("latest_revenue_growth", diagnostics.get("revenue_growth"))
        operating = "混合或尚不能判断"
        if growth is not None:
            operating = "最近可比期间收入增长；利润与现金持续性待验证" if number(growth) > 0 else "最近可比期间收入承压；原因与持续性待验证"
        if q["monitors"]:
            operating = "经营信号混合：收入变化与现金回报风险需分别检验，不能仅凭收入确认改善"
        if review["verdict"] == "refuted":
            operating = "原研究假设受反证，需要撤回或重建"
        conclusion = self.store.add(db, "conclusion", issuer, dict(
            version=len(prior)+1, previous_id=prior[-1]["id"] if prior else None,
            review_actor=review["reviewed_by"],
            reason=reason, fingerprint=fingerprint, run_id=run["id"], review_id=review["id"],
            kernel_digest=RUNNING_KERNEL, permitted_use="流程与敏感性研究；研究结论有效性未通过验收",
            hypothesis=self.current_hypothesis(db, issuer), operating_direction=operating,
            security_direction="无法判断现价吸引力：缺少可比现价、证券股本及充分估值依据",
            business_quality="当前保留主假设与反方，未把局部财务核验升级为护城河已证实",
            confidence=dict(facts=f"{q['verified']}项局部核验，{len(q['conflicts'])}组冲突，{q['candidates']}项候选",
                            explanation="较弱或有条件：关键经营解释仍待补证" if q["gaps"] else "需人工判断，未提供概率",
                            valuation="情景参数已人工审议，仍受模型边界约束" if run["assumptions_confirmed"] else "默认情景未审议，只用于敏感性研究",
                            probability="未校准；不提供上涨概率"),
            action="撤回主假设并补证" if review["verdict"] == "refuted" else "继续研究 / 等待关键证据",
            readiness="暂缓估值结论" if run["status"] == "blocked" else "有条件研究结论",
            gaps=q["gaps"], fact_ids=[i["fact_id"] for i in run["inputs"]],
            next_validation=review["falsifier"], account_action="未提供账户约束，不形成个性化仓位动作"))
        self.store.log(db, issuer, "结论版本发布", {"conclusion_id": conclusion["id"], "version": conclusion["version"], "reason": reason})
        return conclusion

    def view(self, issuer):
        with self.store.tx() as db:
            company = self.issuer(db, issuer)
            q = self.quality(db, issuer)
            fingerprint = self.fingerprint(db, issuer)
            conclusions = self.store.list(db, "conclusion", issuer)
            runs = self.store.list(db, "model_run", issuer)
            reviews = self.store.list(db, "review", issuer)
            for item in conclusions + runs + reviews:
                item["stale"] = item["fingerprint"] != fingerprint
            if runs:
                for item in conclusions:
                    item["stale"] |= item["run_id"] != runs[-1]["id"]
            if reviews:
                for item in conclusions:
                    item["stale"] |= item["review_id"] != reviews[-1]["id"]
            if reviews and runs:
                reviews[-1]["stale"] |= reviews[-1]["run_id"] != runs[-1]["id"]
            jobs = [dict(r, payload=json.loads(r["payload"])) for r in db.execute(
                "SELECT * FROM jobs WHERE issuer=? ORDER BY created_at DESC", (issuer,))]
            return dict(company=company, revision=self.store.revision(db, issuer),
                        hypothesis=self.current_hypothesis(db, issuer), quality=q,
                        documents=self.store.list(db, "document", issuer),
                        models=runs, reviews=reviews, conclusions=conclusions,
                        events=self.store.list(db, "event", issuer), jobs=jobs,
                        defaults=self.defaults(company), history=self.store.history(db, issuer))

    def dashboard(self):
        with self.store.tx() as db:
            companies = self.store.list(db, "issuer")
        result = []
        for company in companies:
            view = self.view(company["id"])
            last = view["conclusions"][-1] if view["conclusions"] else None
            result.append(dict(company, facts=len(view["quality"]["facts"]),
                               verified=view["quality"]["verified"], gaps=len(view["quality"]["gaps"]),
                               conflicts=len(view["quality"]["conflicts"]),
                               conclusion=last, documents=len(view["documents"]), revision=view["revision"]))
        return result

    def command(self, issuer, action, data):
        with self.store.tx() as db:
            self.issuer(db, issuer)
            self.expect(db, issuer, data.get("expected_revision"))
            if action == "fact":
                return self.add_fact(db, issuer, data)
            if action == "check":
                return self.check_fact(db, issuer, data["fact_id"], data["status"], data["reason"])
            if action == "model":
                item = self.build_model(db, issuer, data.get("assumptions"), data.get("rationale", ""), data.get("confirmed", False))
                self.store.log(db, issuer, "模型重算", {"run_id": item["id"], "status": item["status"]})
                return item
            if action == "review":
                return self.review(db, issuer, data)
            if action == "publish":
                return self.publish(db, issuer, data["reason"])
            if action == "hypothesis":
                for key in ("question", "thesis", "counter_thesis", "transmission"):
                    if len(data.get(key, "").strip()) < 12:
                        raise ValueError("问题、主假设、反方和传导各需至少十二字符")
                item = self.store.add(db, "hypothesis", issuer, {k: data[k] for k in ("question", "thesis", "counter_thesis", "transmission")})
                self.store.log(db, issuer, "研究问题更新", {"hypothesis_id": item["id"]})
                return item
            if action == "event":
                for key in ("title", "mechanism", "unknown", "next_validation", "source_url", "published_at"):
                    if not data.get(key):
                        raise ValueError("事件缺少" + key)
                if not data["source_url"].startswith("https://"):
                    raise ValueError("事件应关联HTTPS原始来源")
                date.fromisoformat(data["published_at"])
                item = self.store.add(db, "event", issuer, {k: data[k] for k in ("title", "mechanism", "unknown", "next_validation", "source_url", "published_at")})
                self.store.log(db, issuer, "事件影响待复核", {"event_id": item["id"], "mechanism": data["mechanism"]})
                return item
            if action == "gap":
                quality = self.quality(db, issuer)
                gaps = {g["key"]: g for g in quality["gaps"]+quality["resolved_gaps"]}
                if data["gap_key"] not in gaps or len(data.get("reason", "").strip()) < 12:
                    raise ValueError("请选择实际缺口并说明处理或停止理由，至少十二字符")
                disposition=data.get("disposition", "pending")
                if disposition not in ("pending","wait","accept_unknown","exit","resolved"):
                    raise ValueError("补证处理方式无效")
                refs=data.get("fact_ids",[])
                if disposition == "resolved":
                    usable_ids={f["id"] for f in quality["usable"]}
                    if not refs or not set(refs) <= usable_ids or gaps[data["gap_key"]]["blocks"] in ("model","evidence"):
                        raise ValueError("补证完成需关联当前可用核验事实；数字冲突和缺失模型输入必须先实质修复")
                item = self.store.add(db, "gap_resolution", issuer, dict(gap_key=data["gap_key"], reason=data["reason"], disposition=disposition, fact_ids=refs))
                self.store.log(db, issuer, "补证或停止决定", {"gap_key": data["gap_key"], "reason": data["reason"]})
                return item
            raise ValueError("不支持的研究动作")
