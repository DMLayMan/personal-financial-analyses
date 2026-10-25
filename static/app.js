"use strict";
const state = {
  csrf: "",
  pageName: "foundation",
  foundationTab: "overview",
  marketTab: "board",
  marketGroup: "all",
  marketRegion: "all",
  industryGroup: "all",
  industryId: null,
  platform: null,
  markets: null,
  industries: null,
  report: null,
  companies: [],
  id: null,
  view: null,
  tab: "report",
  doc: null,
  page: 1,
};
const $ = (s) => document.querySelector(s);
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const link = (url, text) =>
  String(url ?? "").startsWith("https://")
    ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(text)}</a>`
    : esc(text);
const tag = (text, kind = "") =>
  `<span class="tag ${esc(kind)}">${esc(text)}</span>`;
const fmt = (v, ratio = false) =>
  v == null
    ? "缺失"
    : ratio
      ? `${(Number(v) * 100).toFixed(2)}%`
      : Math.abs(Number(v)) >= 1e8
        ? `${(Number(v) / 1e8).toLocaleString("zh-CN", { maximumFractionDigits: 2 })} 亿`
        : Number(v).toLocaleString("zh-CN", { maximumFractionDigits: 4 });
const when = (v) =>
  v
    ? new Date(v).toLocaleString("zh-CN", {
        timeZone: "Asia/Shanghai",
        hour12: false,
      })
    : "时间未知";
const empty = (text) => `<div class="empty">${esc(text)}</div>`;
const tabs = {
  report: "研究报告",
  overview: "研究问题",
  evidence: "资料与证据",
  gaps: "主动补证",
  models: "盈利与估值",
  review: "反方审查",
  conclusion: "结论与更新",
};
const sourcePage = (locator) =>
  Number(String(locator || "").match(/PDF\s*(?:第|p\.?\s*)(\d+)/i)?.[1]) || 1;
const scenarioNames = { downside: "下行", base: "基准", upside: "上行" };
function toast(message, error = false) {
  $("#toast").textContent = message;
  $("#toast").className = error ? "error" : "";
  $("#toast").hidden = false;
  clearTimeout(state.toast);
  state.toast = setTimeout(() => ($("#toast").hidden = true), 7000);
}
async function api(path, data) {
  const options =
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-PFA-Token": state.csrf,
          },
          body: JSON.stringify(data),
        };
  const r = await fetch(path, options);
  let j;
  try {
    j = await r.json();
  } catch {
    throw new Error("本地服务未返回有效数据");
  }
  if (!r.ok) throw new Error(j.error || "请求失败");
  return j;
}
async function refresh() {
  const b = await api("/api/bootstrap");
  state.csrf = b.csrf;
  state.companies = b.companies;
  [state.platform, state.markets, state.industries] = await Promise.all([
    api("/api/platform"),
    api("/api/markets"),
    api("/api/industries"),
  ]);
  renderNav();
  if (state.id) await loadCompany(state.id);
  else renderHome();
}
function renderNav() {
  const names = {
    msft: "微软",
    cost: "Costco",
    tencent: "腾讯",
    byd: "比亚迪",
    catl: "宁德时代",
    cmb: "招商银行",
  };
  $("#company-nav").innerHTML = state.companies
    .map(
      (c) =>
        `<button class="nav-item company-nav ${state.id === c.id ? "active" : ""}" data-company="${esc(c.id)}"><span class="company-initial">${esc(c.id.slice(0, 2).toUpperCase())}</span><span class="company-name">${esc(names[c.id] || c.name)}<small>${esc(c.market)} · ${esc(c.currency)}</small></span><span class="company-badge">${c.gaps}</span></button>`,
    )
    .join("");
  document
    .querySelectorAll("[data-page]")
    .forEach((b) =>
      b.classList.toggle("active", b.dataset.page === state.pageName),
    );
}
function renderHome() {
  renderWorkspace();
}
function principles() {
  return `<div class="principles"><div><h3>能力圈与资本回报</h3><p>业务理解、维持投入和买入条件分别检验，熟悉产品不能替代证据。</p>${link("https://www.berkshirehathaway.com/letters/1996.html", "巴菲特 · 1996 股东信 ↗")}</div><div><h3>逆向思考与激励</h3><p>说明最强反方如何成立，寻找会推翻主判断的观察。</p>${link("https://www.stripe.press/poor-charlies-almanack/talk-four", "芒格 · 原始演讲 ↗")}</div><div><h3>永久损失与持有能力</h3><p>经营、融资与估值联合施压；模型的下行情景不是最大损失上限。</p>${link("https://www.oaktreecapital.com/docs/default-source/memos/2015-06-08-risk-revisited-again.pdf", "霍华德·马克斯 · 风险备忘录 ↗")}</div></div>`;
}
async function loadCompany(id) {
  const [v, report] = await Promise.all([
    api("/api/companies/" + encodeURIComponent(id)),
    api("/api/reports/" + encodeURIComponent(id)),
  ]);
  state.report = report;
  state.pageName = "cases";
  state.id = id;
  state.view = v;
  renderNav();
  renderCompany();
}
function renderCompany() {
  const v = state.view,
    c = v.company,
    last = v.conclusions.at(-1);
  $("#content").innerHTML =
    `<p class="eyebrow">Company research / ${esc(c.market)}</p><div class="heading-row"><div><h1>${esc(c.name)}</h1><p class="meta">${esc(c.currency)} 报告币种 · ${v.documents.length} 份原文 · ${v.quality.verified} 项已核验 · 时间显示 Asia/Shanghai</p></div><button data-action="export" class="small">导出研究记录 ↗</button></div>${last?.stale ? '<div class="note danger">研究输入或模型已变化。旧结论已标记待更新，请核对当前模型并重新审查。</div>' : ""}<nav class="tabs" aria-label="研究步骤">${Object.entries(
      tabs,
    )
      .map(
        ([k, title]) =>
          `<button data-tab="${k}" class="${state.tab === k ? "active" : ""}">${title}${k === "gaps" ? ` <small>${v.quality.gaps.length}</small>` : ""}</button>`,
      )
      .join(
        "",
      )}</nav>${{ report: reportView, overview: overview, evidence: evidence, gaps: gaps, models: models, review: review, conclusion: conclusion }[state.tab]()}`;
}
function overview() {
  const v = state.view,
    h = v.hypothesis;
  return `<div class="grid">${monitorCards(v.quality.monitors)}<section class="card"><p class="eyebrow">Research question</p><h2>${esc(h.question)}</h2><div class="key-line"><span>主假设</span><div>${esc(h.thesis)}</div></div><div class="key-line"><span>最强替代解释</span><div>${esc(h.counter_thesis)}</div></div><div class="key-line"><span>盈利传导</span><div>${esc(h.transmission)}</div></div><div class="note">这是待检验研究假设。支持与反对证据、模型和复核必须分步完成，不能把假设直接当作结论。</div></section><section class="card"><h2>本轮研究进度</h2>${progress(v)}<h3 class="section-gap">下一项有价值的工作</h3><p class="muted">${esc(nextStep(v))}</p><button class="primary" data-tab="${!v.models.length ? "models" : !v.reviews.length ? "review" : v.conclusions.length ? "gaps" : "conclusion"}">继续研究 →</button></section><section class="card full"><details><summary>修改问题、假设与传导机制</summary><form data-form="hypothesis" class="section-gap">${["question", "thesis", "counter_thesis", "transmission"].map((k, i) => `<label><span>${["研究问题", "主假设", "最强替代解释", "从经营到财务的传导"][i]}</span><textarea name="${k}" required minlength="12">${esc(h[k])}</textarea></label>`).join("")}<button class="primary">保存新版本</button></form></details></section><section class="card full"><h2>方法交叉检验</h2>${principles()}<p class="muted section-gap">原作者的思想用于提问与反证，不代表他们对当前公司作出判断，也不以“流派投票”形成可信度。</p></section></div>`;
}
function progress(v) {
  const m = v.models.at(-1),
    r = v.reviews.at(-1),
    c = v.conclusions.at(-1);
  return [
    ["资料获取", `${v.documents.length} 份原文已保存`],
    [
      "证据核验",
      `${v.quality.verified} 项局部核验 / ${v.quality.candidates} 项候选`,
    ],
    ["主动补证", `${v.quality.gaps.length} 个缺口，关键未知保留`],
    [
      "盈利与估值",
      m
        ? m.stale
          ? "输入已变化，待重算"
          : m.status === "blocked"
            ? "关键输入缺失，已限制模型"
            : "可复算情景已生成"
        : "待运行",
    ],
    ["反方审查", r ? (r.stale ? "待重新审查" : "已有分步审查记录") : "待审查"],
    [
      "结论更新",
      c
        ? c.stale
          ? "旧结论待更新"
          : `第 ${c.version} 版 · 有条件`
        : "待形成条件结论",
    ],
  ]
    .map(
      ([a, b]) =>
        `<div class="key-line"><span>${a}</span><div>${esc(b)}</div></div>`,
    )
    .join("");
}
function nextStep(v) {
  const m = v.models.at(-1),
    r = v.reviews.at(-1);
  if (!m || m.stale)
    return "在当前核验事实与明确假设上重算盈利和估值，检查缺口如何限制结果。";
  if (!r || r.stale)
    return "用具体证据写出最强反方、实质回应和可观察的推翻条件。";
  if (!v.conclusions.length)
    return "解释结论范围、可信度和剩余未知，发布可追踪的条件结论。";
  return "按缺口对决定的影响安排补证；不能因资料更多就自动提高信心。";
}
function monitorCards(monitors) {
  return monitors
    .map(
      (m) =>
        `<section class="card full"><div class="card-heading"><h2>${esc(m.title)}</h2>${tag("重点核查", "danger")}</div>${m.change != null ? `<p class="mono">单季 CFO ${fmt(m.current)} / 上年同期 ${fmt(m.prior)} · 同比 ${fmt(m.change, true)}</p>` : ""}<p>${esc(m.mechanism)}</p><p class="muted">下一来源：${esc(m.next_source)}<br>触发规则：${esc(m.rule)}</p><button class="small" data-tab="gaps">安排补证 →</button></section>`,
    )
    .join("");
}
function fetchForm(gapKey = "", url = "") {
  const c = state.view.company;
  return `<form data-form="fetch"><input name="gap_key" type="hidden" value="${esc(gapKey)}"><div class="form-grid"><label class="wide"><span>HTTPS 原文地址（监管 / 公司官网）</span><input name="url" type="url" required placeholder="https://…" value="${esc(url)}"></label><label><span>资料标题</span><input name="title" required placeholder="说明资料如何帮助区分解释"></label><label><span>首次公开日期（不确定可留空）</span><input name="published_at" type="date"></label></div><input name="currency" type="hidden" value="${esc(c.currency)}"><input name="scope" type="hidden" value="consolidated"><div class="form-foot"><button class="primary">加入获取队列</button><span class="muted">获取成功后仍需提取、核验和判断是否解决缺口。</span></div></form>`;
}
function evidence() {
  const v = state.view;
  return `<div class="grid"><section class="card full"><div class="card-heading"><h2>原始资料与版本</h2>${tag("读取 ≠ 核验 ≠ 持续更新", "neutral")}</div>${v.documents.map((d) => `<article class="doc"><h3>${esc(d.title)}</h3><div class="meta">公开 ${esc(d.published_at || "未知")} · 取得 ${when(d.retrieved_at)} · ${esc(d.basis || "待核对")} / ${esc(d.scope || "待核对")}</div><div class="hash mono">SHA256 ${esc(d.sha256)}</div><div class="doc-actions">${link(d.url, "打开原文 ↗")}<button class="small" data-doc="${esc(d.id)}">查看本地正文</button>${tag("持续获取未验证", "warn")}</div>${d.notes ? `<p class="muted">${esc(Array.isArray(d.notes) ? d.notes.join("；") : d.notes)}</p>` : ""}</article>`).join("")}</section><section class="card full"><details><summary>获取新的公开资料</summary><div class="section-gap">${fetchForm()}</div></details></section><section class="card full"><div class="card-heading"><h2>事实台账</h2><span class="muted">${v.quality.facts.length} 项 · 不同口径分别保存</span></div><input id="fact-filter" class="fact-filter" placeholder="筛选指标、期间或口径" aria-label="筛选事实"><div class="table-wrap"><table><thead><tr><th>指标 / 口径</th><th>期间</th><th class="number">值 / 单位</th><th>核验</th><th>来源与动作</th></tr></thead><tbody>${v.quality.facts.map((f) => `<tr data-fact-search="${esc([f.label, f.metric, f.period_start, f.period_end, f.basis].join(" ").toLowerCase())}"><td>${esc(f.label)}<div class="meta">${esc(f.scope)} / ${esc(f.basis)}</div>${tag(f.evidence_label, "neutral")}</td><td class="mono">${esc(f.period_start || "时点")}<br>${esc(f.period_end)}</td><td class="number mono">${fmt(f.value, f.unit === "ratio")}<div class="meta">${esc(f.unit)}</div></td><td>${tag({ verified: "局部已核验", candidate: "提取候选", rejected: "已撤回" }[f.status], f.status === "verified" ? "" : f.status === "rejected" ? "danger" : "warn")}</td><td><details><summary>原文与核验记录</summary><p>${esc(f.locator)}</p><p>原数：${esc(f.raw_value || f.quote)} ${esc(f.raw_unit || "")}</p><p>${esc(f.note)}</p>${link(f.source.url, "原文 ↗")}<p class="muted">${esc(f.check?.reason || "尚未核验")}</p><button class="small" data-doc="${esc(f.document_id)}" data-source-page="${sourcePage(f.locator)}">本地正文</button><button class="small" data-check="${esc(f.id)}" data-status="verified">核验</button><button class="small danger" data-check="${esc(f.id)}" data-status="rejected">撤回</button></details></td></tr>`).join("")}</tbody></table></div></section><section class="card full"><details><summary>从原文提取一条新事实（先进入候选）</summary><form data-form="fact" class="section-gap"><div class="form-grid"><label class="wide"><span>所属原文版本</span><select name="document_id">${v.documents.map((d) => `<option value="${esc(d.id)}">${esc(d.title)}</option>`).join("")}</select></label><label><span>标准指标</span><select name="metric">${Object.entries(
    {
      revenue: "营业收入",
      net_income: "归属净利润",
      operating_cash_flow: "经营现金流",
      capex_cash: "现金资本投入",
      common_equity: "普通股权益",
      nim: "净利息收益率",
      cash: "现金",
      shares_outstanding: "期末实际股数",
    },
  )
    .map(([k, n]) => `<option value="${k}">${n}</option>`)
    .join(
      "",
    )}</select></label><label><span>值（原始精度，换算为元 / 股 / 小数比率）</span><input name="value" required inputmode="decimal"></label><label><span>单位</span><select name="unit"><option>${esc(v.company.currency)}</option><option>shares</option><option>ratio</option></select></label><label><span>会计口径（与原文一致）</span><input name="basis" required placeholder="US GAAP / IFRS / CAS"></label><label><span>期间开始（时点值可留空）</span><input name="period_start" type="date"></label><label><span>期间结束</span><input name="period_end" type="date" required></label><label><span>范围</span><select name="scope"><option value="consolidated">合并</option><option value="parent">母公司 / 母行</option></select></label><label><span>页码或原文锚点</span><input name="locator" required></label><label class="wide"><span>短原文或原始数字</span><input name="quote" required></label><label class="wide"><span>定义及提取注意事项</span><textarea name="note"></textarea></label></div><button class="primary">保存候选事实</button></form></details></section></div>`;
}
function gaps() {
  const v = state.view;
  return `<div class="grid">${v.quality.resolved_gaps?.length ? `<section class="card full"><h2>已提交的补证回应</h2>${v.quality.resolved_gaps.map((g) => `<div class="task"><h3>${esc(g.title)}</h3><p>${esc(g.handling.reason)}</p><p class="muted">${esc(g.state)} · 已关联 ${g.handling.fact_ids.length} 项核验事实。资料撤回后将自动重开。</p></div>`).join("")}</section>` : ""}<section class="card full"><h2>优先获取能改变判断的证据</h2><p class="muted">缺口按决定影响优先排列。处理记录不等于问题已解决；缺少可验证信息时，可以接受未知并暂缓相应结论。</p>${v.quality.gaps.map((g, i) => `<article class="task"><div class="card-heading"><h3><span class="priority">${String(i + 1).padStart(2, "0")} / ${esc(g.priority)}</span>　${esc(g.title)}</h3>${tag(g.handling ? "已有处理记录" : "待补证", g.handling ? "neutral" : "warn")}</div><p>${esc(g.why)}</p><p class="muted">下一来源：${esc(g.next_source)} · 限制层次：${esc(g.blocks)}</p><p class="muted">${esc(g.decision_impact)} ${esc(g.stop_rule)}</p>${g.handling ? `<div class="note">${esc(g.handling.reason)}<br><small>仍保留原缺口；不会自动升级可信度。</small></div>` : ""}<details><summary>安排获取，或记录补证 / 停止理由</summary><form data-form="gap"><input type="hidden" name="gap_key" value="${esc(g.key)}"><label><span>处理方式</span><select name="disposition"><option value="pending">继续寻找区分性证据</option><option value="wait">等待后续披露</option><option value="accept_unknown">接受未知，限制相应结论</option><option value="exit">退出此项判断</option><option value="resolved">已有核验依据，提交补证回应</option></select></label><label><span>为什么值得补证 / 为什么本轮停止？什么变化会重开？</span><textarea name="reason" required minlength="12"></textarea></label><label><span>若提交补证回应，选择当前可用核验事实</span><select name="fact_ids" multiple size="4">${v.quality.usable.map((f) => `<option value="${esc(f.id)}">${esc(f.label)} · ${esc(f.period_end)} · ${fmt(f.value, f.unit === "ratio")}</option>`).join("")}</select></label><button>保存处理记录</button></form><h3 class="section-gap">已找到准确原文地址时</h3>${fetchForm(g.key, g.target_url || "")}</details></article>`).join("") || empty("当前没有登记缺口。这不代表所有风险均已排除。")}</section><section class="card full"><h2>资料任务与健康状态</h2>${v.jobs.map((j) => `<div class="task"><div class="card-heading"><h3>${esc(j.payload.title || j.payload.url)}</h3>${tag({ queued: "排队中", running: "获取中", succeeded: "取得原文，待提取", failed: "获取失败" }[j.status], j.status === "failed" ? "danger" : "neutral")}</div><p class="meta">尝试 ${j.attempts}/3 · ${when(j.updated_at)}</p><p class="muted source-url">${esc(j.payload.url)}</p>${j.error ? `<p>${esc(j.error)}</p>` : ""}${j.status === "failed" && j.attempts < 3 ? `<button class="small" data-retry="${esc(j.id)}">重试</button>` : ""}</div>`).join("") || empty("尚无后台取数任务。应用仅在本地服务运行时处理队列，没有开启定时全市场监控。")}</section></div>`;
}
function models() {
  const v = state.view,
    m = v.models.at(-1),
    bank = v.company.sector === "bank",
    a = m?.assumptions || v.defaults;
  const fields = bank
    ? {
        roe: "持续普通股 ROE",
        discount_rate: "股权成本",
        payout: "预测期分红比例",
        terminal_growth: "终值增长率",
      }
    : {
        growth: "年收入增长率",
        margin_change: "五年末净利率变化",
        terminal_pe: "第五年末 PE",
        discount_rate: "股权成本",
        payout: "利润分配假设",
      };
  return `<div class="stack"><section class="card"><div class="card-heading"><h2>${bank ? "银行普通股剩余收益" : "盈利预测与股权价值情景"}</h2>${tag(m?.stale ? "输入已变，待重算" : m ? "已有可追溯运行" : "待运行", m?.stale ? "danger" : "neutral")}</div><div class="note warn">${bank ? "使用普通股权益和净盈余关系，检查资本约束、OCI与分配。" : "以同期间年度收入与归属净利作为基线，不把半年数乘二。股权价值来自明确的盈利、分配与终值倍数假设，未等同于完整现金流DCF。"} 默认参数用于探索敏感性，不能直接解释为预测。</div><form data-form="model"><div class="assumptions-grid">${Object.entries(
    scenarioNames,
  )
    .map(([key]) => {
      const params = a[key];
      return `<section><h3>${scenarioNames[key]}</h3>${Object.entries(fields)
        .map(
          ([f, title]) =>
            `<label><span>${title}${f !== "terminal_pe" ? "（小数）" : ""}</span><input name="${key}.${f}" value="${esc(params[f])}" required inputmode="decimal"></label>`,
        )
        .join("")}</section>`;
    })
    .join(
      "",
    )}</div><label class="section-gap"><span>假设依据、最敏感变量及尚未验证的条件</span><textarea name="rationale" placeholder="参数来自哪条经营判断？什么数据会使它不成立？">${esc(m?.rationale || "")}</textarea></label><label class="checklabel"><input type="checkbox" name="confirmed" ${m?.assumptions_confirmed ? "checked" : ""}>我已审议这些假设和适用边界（不代表事实或预测已经得到验证）</label><div class="form-foot"><button class="primary">在当前证据上重算</button><span class="muted">十进制计算 · 冻结输入版本 · 保留旧运行</span></div></form></section>${m ? modelResult(m) : empty("运行后查看经营诊断、三种情景、公式、输入来源和限制。")}</div>`;
}
function modelResult(m) {
  const diagNames = {
    latest_revenue_growth: "最近披露的同期间收入同比",
    latest_nim: "最近披露净利息收益率",
    latest_credit_cost: "最近披露信用成本",
    latest_net_income: "最近披露普通股净利润",
    latest_net_interest_income: "最近披露净利息收入",
    latest_cet1: "最近披露核心一级资本充足率",
    net_margin: "年度归属净利率",
    revenue_growth: "年度收入增速",
    net_income_growth: "年度净利润增速",
    cash_conversion: "CFO / 净利润",
    cfo_less_cash_capex: "CFO − 现金资本支付",
    cash_capex_to_cfo: "现金资本支付 / CFO",
    margin_100bp_profit_sensitivity: "净利率变化100bp的年利润单位敏感性",
    roe_100bp_profit_sensitivity: "ROE变化100bp的年利润单位敏感性",
  };
  return `<section class="card"><div class="card-heading"><h2>经营诊断与模型结果</h2><span class="muted">基线期末 ${esc(m.baseline_as_of || "缺失")} · ${when(m.created_at)}</span></div>${m.issues.map((i) => `<div class="note danger">${esc(i)}</div>`).join("")}<div class="table-wrap"><table><tbody>${Object.entries(
    m.diagnostics,
  )
    .map(
      ([k, value]) =>
        `<tr><td>${esc(diagNames[k] || k)}</td><td class="number mono">${fmt(value, ["net_margin", "revenue_growth", "net_income_growth", "cash_capex_to_cfo", "latest_nim", "latest_credit_cost", "latest_cet1", "latest_revenue_growth"].includes(k))}</td></tr>`,
    )
    .join("")}</tbody></table></div><div class="assumptions-grid">${Object.keys(
    scenarioNames,
  )
    .filter((k) => m.scenarios[k])
    .map((k) => {
      const s = m.scenarios[k];
      return `<article class="valuation-card"><span class="muted">${scenarioNames[k]} · 总普通股权益价值情景</span><strong>${fmt(s.total_equity)} ${esc(m.currency)}</strong><p class="muted">${esc(s.method)}</p><details><summary>五年预测与计算公式</summary><p class="mono muted">${esc(s.formula)}</p><div class="table-wrap"><table><thead><tr><th>年</th><th class="number">归属利润</th><th class="number">${s.rows[0]?.revenue ? "收入" : "期末普通股权益"}</th></tr></thead><tbody>${s.rows.map((r) => `<tr><td>Y${r.year}</td><td class="number">${fmt(r.net_income)}</td><td class="number">${fmt(r.revenue || r.closing_equity)}</td></tr>`).join("")}</tbody></table></div>${s.terminal_payout != null ? `<p class="muted">终值净盈余所需分红率 ${fmt(s.terminal_payout, true)}，与预测期分别处理。</p>` : ""}</details></article>`;
    })
    .join(
      "",
    )}</div><ul class="warnings">${m.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul><details><summary>查看被冻结的输入、期间和来源</summary><div class="table-wrap"><table><thead><tr><th>输入角色</th><th>值</th><th>期间 / 口径</th><th>依据</th></tr></thead><tbody>${m.inputs.map((i) => `<tr><td>${esc(i.role)}</td><td class="mono">${esc(i.value)} ${esc(i.currency)}</td><td>${esc(i.period_start || "时点")} — ${esc(i.period_end)}<br>${esc(i.basis)}</td><td>${esc(i.locator)}<br><button class="small" data-doc="${esc(i.source_id)}">原文</button></td></tr>`).join("")}</tbody></table></div><div class="hash mono">研究输入 ${esc(m.fingerprint)}</div></details></section>`;
}
function review() {
  const v = state.view,
    r = v.reviews.at(-1),
    m = v.models.at(-1);
  return `<div class="grid"><section class="card full"><h2>让反方有权改变结论</h2><p class="muted">独立写出最强替代解释，再回应。多次调用同一个模型或重复同一来源，不等于独立验证。当前审查由个人研究者完成。</p>${!m || m.stale ? '<div class="note warn">先在最新证据上重算模型，再提交审查。</div>' : ""}<form data-form="review"><label><span>最强反方：什么机制会使主判断失败？</span><textarea name="strongest_counter" required minlength="12" placeholder="具体解释如何损失、受哪些证据支持">${esc(r?.strongest_counter || v.hypothesis.counter_thesis)}</textarea></label><label><span>实质回应：哪些已被证实，哪些仍然未知？</span><textarea name="response" required minlength="12">${esc(r?.response || "")}</textarea></label><label><span>可观察推翻条件与下一验证点</span><textarea name="falsifier" required minlength="12">${esc(r?.falsifier || "")}</textarea></label><label><span>审查所依据的事实（至少一项；包括反方依据）</span></label><div class="review-evidence">${v.quality.facts
    .filter((f) => f.status === "verified")
    .map(
      (f) =>
        `<label class="checklabel"><input name="fact_ids" type="checkbox" value="${esc(f.id)}" ${r?.fact_ids.includes(f.id) ? "checked" : ""}>${esc(f.label)} · ${esc(f.period_end)} · ${fmt(f.value, f.unit === "ratio")} ${esc(f.unit)} · ${esc(f.locator)}</label>`,
    )
    .join(
      "",
    )}</div><label><span>审查结果</span><select name="verdict"><option value="conditional">主判断仍有条件，继续补证</option><option value="refuted">反方已使主判断失效，撤回或重建</option><option value="supported">现有证据支持主判断，但保留边界</option></select></label><label><span>本次审查记录来源</span><select name="actor"><option value="local_researcher" ${r?.reviewed_by === "implementation_acceptance" ? "" : "selected"}>研究者本人审议</option><option value="implementation_acceptance" ${r?.reviewed_by === "implementation_acceptance" ? "selected" : ""}>流程验证，尚未经本人独立审议</option></select></label><button class="primary" ${!m || m.stale ? "disabled" : ""}>保存本轮反方审查</button></form></section>${r ? `<section class="card full"><h2>最近审查记录 ${tag(r.stale ? "已过期，需复核" : "关联当前模型", r.stale ? "danger" : "neutral")}</h2><p>${esc(r.strongest_counter)}</p><p class="muted">${esc(r.response)}</p><p class="muted">${when(r.created_at)} · ${esc(r.reviewed_by)} · ${esc(r.independence)}</p></section>` : ""}</div>`;
}
function conclusion() {
  const v = state.view,
    last = v.conclusions.at(-1),
    r = v.reviews.at(-1);
  return `<div class="stack">${last ? conclusionCard(last) : empty("尚未形成结论。完成模型与反方审查后，可发布明确边界的条件结论。")}<section class="card"><h2>发布或更新结论</h2><p class="muted">系统从当前模型、反方审查与缺口形成结构化记录。不会生成总置信分、上涨概率或个性化仓位建议。</p><form data-form="publish"><label><span>本次形成 / 改变判断的理由</span><textarea name="reason" required minlength="12" placeholder="相较旧版，新证据改变了什么？哪些仍然不成立？"></textarea></label><button class="primary" ${!r || r.stale ? "disabled" : ""}>保存新的条件结论</button>${!r || r.stale ? '<span class="muted">　请先完成当前模型的反方审查</span>' : ""}</form></section><section class="card"><details><summary>记录新事件及其传导，触发重新研究</summary><form data-form="event" class="section-gap"><div class="form-grid"><label><span>事件标题</span><input name="title" required></label><label><span>公开日期</span><input type="date" name="published_at" required></label><label class="wide"><span>原始来源</span><input name="source_url" type="url" required placeholder="https://…"></label><label class="wide"><span>暴露 → 传导环节 → 盈利 / 现金 / 估值 → 时滞与抵消</span><textarea name="mechanism" required></textarea></label><label class="wide"><span>关键未知：缺哪些暴露、转嫁或财务口径？</span><textarea name="unknown" required></textarea></label><label class="wide"><span>下一验证点与研究动作</span><textarea name="next_validation" required></textarea></label></div><button>登记事件，标记旧结论待更新</button></form></details>${
    v.events.length
      ? '<hr class="divider">' +
        v.events
          .slice()
          .reverse()
          .map(
            (e) =>
              `<article class="task"><h3>${esc(e.title)} ${tag(e.published_at, "neutral")}</h3><p>${esc(e.mechanism)}</p><p class="muted">未知：${esc(e.unknown)}<br>下一验证：${esc(e.next_validation)}</p>${link(e.source_url, "原始来源 ↗")}</article>`,
          )
          .join("")
      : ""
  }</section><section class="card"><h2>结论版本</h2>${
    v.conclusions.length
      ? v.conclusions
          .slice()
          .reverse()
          .map(
            (c) =>
              `<details class="task"><summary>V${c.version} · ${when(c.created_at)} · ${esc(c.reason)}</summary>${conclusionCard(c)}</details>`,
          )
          .join("")
      : empty("尚无历史结论。旧记录与失败记录会保留。")
  }</section><section class="card"><h2>研究与决定日志</h2><div class="timeline">${v.history
    .slice(0, 45)
    .map(
      (h) =>
        `<article class="entry"><h3>${esc(h.action)}</h3><p class="meta">${when(h.created_at)} · #${h.sequence}</p><p class="muted">${esc(h.payload.reason || h.payload.metric || h.payload.url || h.payload.status || h.payload.verdict || "记录版本与依赖关系")}</p></article>`,
    )
    .join("")}</div></section></div>`;
}
function conclusionCard(c) {
  return `<section class="card"><div class="card-heading"><h2>条件结论 · V${c.version}</h2>${tag(c.stale ? "证据已变化" : c.readiness, c.stale ? "danger" : "warn")}</div><div class="key-line"><span>经营方向</span><div>${esc(c.operating_direction)}</div></div><div class="key-line"><span>商业质量</span><div>${esc(c.business_quality)}</div></div><div class="key-line"><span>证券经济性</span><div>${esc(c.security_direction)}</div></div><div class="key-line"><span>当前动作</span><div>${esc(c.action)}</div></div><div class="key-line"><span>事实核验</span><div>${esc(c.confidence.facts)}</div></div><div class="key-line"><span>解释信心</span><div>${esc(c.confidence.explanation)}</div></div><div class="key-line"><span>估值与预测</span><div>${esc(c.confidence.valuation)}<br>${esc(c.confidence.probability)}</div></div><div class="key-line"><span>下一验证</span><div>${esc(c.next_validation)}</div></div><p class="muted">${esc(c.account_action)}</p><div class="meta">${when(c.created_at)} · ${esc(c.reason)}</div>${c.review_actor === "implementation_acceptance" ? '<div class="note warn">这条记录用于首版流程验收，审查意见由开发时的研究者填写，尚未经用户独立复核。</div>' : ""}</section>`;
}
async function command(action, data) {
  const id = state.id;
  const allButtons = [...document.querySelectorAll("button")];
  allButtons.forEach((b) => (b.disabled = true));
  try {
    await api(`/api/companies/${id}/${action}`, {
      ...data,
      expected_revision: state.view.revision,
    });
    await loadCompany(id);
    toast(
      {
        model: "模型已重算并保存输入版本",
        review: "反方审查已保存",
        publish: "条件结论已保存，旧版本保留",
        fetch: "获取任务已入队；完成后仍需核验",
        gap: "处理理由已记录，证据限制仍保留",
        event: "事件已登记，旧判断需重新复核",
      }[action] || "记录已保存",
    );
  } catch (e) {
    toast(e.message, true);
    await loadCompany(id);
  } finally {
    allButtons.forEach((b) => (b.disabled = false));
  }
}
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  try {
    if (await handleWorkspaceClick(b)) return;
    if (b.dataset.company) {
      state.tab = "report";
      await loadCompany(b.dataset.company);
    } else if (b.id === "home") {
      state.id = null;
      renderNav();
      renderHome();
    } else if (b.id === "refresh") {
      await refresh();
      toast("已读取最新本地记录");
    } else if (b.dataset.tab) {
      state.tab = b.dataset.tab;
      renderCompany();
    } else if (b.dataset.check) {
      const reason = prompt(
        "请说明回看了哪一页、如何核验数值 / 期间 / 单位，或为什么撤回。",
      );
      if (reason)
        await command("check", {
          fact_id: b.dataset.check,
          status: b.dataset.status,
          reason,
        });
    } else if (b.dataset.retry) {
      await command("retry", { job_id: b.dataset.retry });
    } else if (b.dataset.doc) {
      state.doc = b.dataset.doc;
      state.page = Number(b.dataset.sourcePage) || 1;
      $("#source-dialog").showModal();
      await showSource();
    } else if (b.id === "close-source") {
      $("#source-dialog").close();
    } else if (b.id === "next-page") {
      state.page++;
      await showSource();
    } else if (b.id === "prev-page") {
      state.page = Math.max(1, state.page - 1);
      await showSource();
    } else if (b.id === "go-page") {
      state.page = Math.max(1, parseInt($("#jump-page").value) || 1);
      await showSource();
    } else if (b.dataset.action === "export") {
      const blob = new Blob(
        [JSON.stringify(await api("/api/export/" + state.id), null, 2)],
        { type: "application/json" },
      );
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `pfa-${state.id}-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    }
  } catch (err) {
    toast(err.message, true);
  }
});
async function showSource() {
  try {
    const j = await api(`/api/documents/${state.doc}?page=${state.page}`);
    $("#source-page").textContent = `第 ${j.page} / ${j.pages} 页或片段`;
    $("#jump-page").value = j.page;
    $("#source-text").textContent = j.text || "没有可提取文字，请回看原始PDF。";
    $("#source-note").textContent = j.note;
    $("#prev-page").disabled = j.page <= 1;
    $("#next-page").disabled = j.page >= j.pages;
  } catch (e) {
    $("#source-text").textContent = e.message;
    $("#source-note").textContent =
      "原文读取失败已明确显示，不代表资料不存在或风险消失。";
  }
}
document.addEventListener("input", (e) => {
  if (e.target.id === "fact-filter") {
    const needle = e.target.value.toLowerCase();
    document
      .querySelectorAll("[data-fact-search]")
      .forEach((r) => (r.hidden = !r.dataset.factSearch.includes(needle)));
  }
});
document.addEventListener("submit", async (e) => {
  const form = e.target;
  if (!form.dataset.form) return;
  e.preventDefault();
  const data = Object.fromEntries(new FormData(form));
  if (form.dataset.form === "model") {
    const assumptions = {};
    for (const [key, value] of Object.entries(data)) {
      if (key.includes(".")) {
        const [s, f] = key.split(".");
        (assumptions[s] ??= {})[f] = value;
        delete data[key];
      }
    }
    data.assumptions = assumptions;
    data.confirmed = form.elements.confirmed.checked;
  }
  if (["review", "gap"].includes(form.dataset.form))
    data.fact_ids = new FormData(form).getAll("fact_ids");
  if (form.dataset.form === "fact") data.currency = state.view.company.currency;
  await command(form.dataset.form, data);
});
refresh().catch((e) => {
  $("#content").innerHTML =
    `<div class="load-error"><h2>本地服务尚未就绪</h2><p>${esc(e.message)}</p><button id="refresh">重新读取</button></div>`;
});
