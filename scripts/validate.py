"""Run real six-company walkthroughs in an isolated database and preserve evidence.

This is implementation/research-flow acceptance, never prediction validation.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pfa.research import Research
from pfa.store import Store, now


RESPONSES = {
    "msft": ("年度利润和收入不能区分AI增量回报，租赁与后续折旧也可能挤压现金收益。", "已核验收入、归属净利和现金投入；CFO减现金Capex只提供现金桥，仍不能识别维持性投入或AI的因果回报。", "后续季度追踪云收入、现金投入与租赁、折旧和投入回报；若回收持续落后投入，重开资本回报假设。"),
    "cost": ("净利润可能受一次性项目影响，会员费递延和日历使销售增长不等于会员经济性持续改善。", "年度同口径收入、净利、现金和资本投入已核验；尚缺续费率、会员分层及正常化利润桥，保留原假设条件。", "取得下一次会员续费率、会员费确认和月销可比口径；若续费恶化或正常化回报走弱，撤回增长持续性。"),
    "tencent": ("排除算力预付款后的调整现金流转正，不能说明现金压力已经解除或AI资本回报已实现。", "报告Q2自由现金流为负且调整后为正，系统已识别定义差异；以2025年度同口径事实做盈利情景，不把预付款加回当现金回收。", "检查预付款履约、后续资本承诺、算力利用率及新增付费收入；若投入持续扩大而回报不足，降低盈利和分配假设。"),
    "byd": ("单月销量上升可能伴随累计销量下降、促销和车型结构恶化，不能直接推出盈利上升。", "已分别保留年度与H1合并数据以及月度和累计销量，EPS按送转后的口径处理；仍需地区结构、单车利润和渠道库存。", "补充地区和车型售价、单车利润、库存和回款；若量增伴随毛利与现金持续恶化，重建竞争和增长判断。"),
    "catl": ("累计现金流看似稳定可能掩盖单季回款和预付款压力，利润增长不能证明现金盈利质量。", "同口径9M减H1的单季CFO同比显著下滑已被规则触发；尚不能断言需求永久受损，需区分营运资金、季节性和客户条款。", "核查应收、预付款、库存与管理层解释，并用下一期实际回款验证；若现金消耗持续且融资收紧，重开价值和生存情景。"),
    "cmb": ("当期年化ROE可能不可持续，零售信用成本上升和净息差压力可能降低普通股资本回报与分配。", "普通股权益、普通股利润与归母利润已分开，NIM与净利差未混用；银行模型采用普通股剩余收益，仍受OCI、资本和信用迁徙未知约束。", "用后续贷款迁徙、信用减值、净息差与资本分配检验可持续ROE；若普通股回报低于资本成本并难以恢复，重估价值。"),
}


def walkthrough(research, actor="implementation_acceptance"):
    results = []
    for company in research.dashboard():
        ident = company["id"]
        view = research.view(ident)
        model = research.command(ident, "model", {"expected_revision": view["revision"]})
        view = research.view(ident)
        counter, response, falsifier = RESPONSES[ident]
        fact_ids = [f["id"] for f in view["quality"]["usable"]]
        review = research.command(ident, "review", dict(expected_revision=view["revision"],
            strongest_counter=counter, response=response, falsifier=falsifier,
            verdict="conditional", fact_ids=fact_ids, actor=actor))
        view = research.view(ident)
        conclusion = research.command(ident, "publish", dict(expected_revision=view["revision"],
            reason="首版本地链路验收：用公开原文局部核验、可复算情景与上述反方形成有条件记录，尚未经用户独立审议。"))
        results.append(dict(issuer=ident, verified=view["quality"]["verified"],
                            documents=len(view["documents"]), model_id=model["id"],
                            review_id=review["id"], conclusion_id=conclusion["id"],
                            scenarios=len(model["scenarios"]), model_status=model["status"],
                            diagnostics=model["diagnostics"], monitors=view["quality"]["monitors"],
                            open_gaps=len(view["quality"]["gaps"]),
                            assumptions_confirmed=model["assumptions_confirmed"],
                            account_action=conclusion["account_action"]))
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(ROOT/"data/acceptance.sqlite3"))
    parser.add_argument("--output", default=str(ROOT/"data/acceptance-report.json"))
    args = parser.parse_args()
    if Path(args.db).exists():
        raise SystemExit("请指定新的验收数据库，保留之前的运行记录。")
    r = Research(Store(args.db))
    r.seed(ROOT/"fixtures/companies.json")
    checks=[]
    for company in r.dashboard():
        for doc in r.view(company["id"])["documents"]:
            p = Path(doc["local_path"])
            if not p.is_absolute():p=ROOT/p
            exists=p.is_file()
            match=exists and hashlib.sha256(p.read_bytes()).hexdigest()==doc["sha256"]
            checks.append(dict(issuer=company["id"],document=doc["title"],exists=exists,sha256_match=match))
    result = dict(run_at=now(), scope="实现与研究流程验收，不是预测绩效", source_checks=checks, companies=walkthrough(r))
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(companies=len(result["companies"]),raw_documents=len(checks),
                         raw_hashes_passed=sum(c["sha256_match"] for c in checks),output=str(path)),ensure_ascii=False))
    if not all(c["sha256_match"] for c in checks):
        raise SystemExit("部分原件缺失或校验失败，不能声明来源包完整。")


if __name__ == "__main__":
    main()
