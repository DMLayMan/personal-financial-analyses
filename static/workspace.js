"use strict";
const foundationTabs = {
  overview: "平台总览",
  methods: "理论与工作流",
  agents: "Agent策略",
  knowledge: "知识与文档",
  review: "审查与验证",
  roadmap: "建设与扩展",
};
const statusLabels = {
  implemented: "已实现",
  partial: "部分实现",
  illustrative: "示例可用",
  planned: "计划中",
};
function pageHeader(en, title, description, extra = "") {
  return `<p class="eyebrow">${esc(en)}</p><div class="heading-row"><div><h1>${esc(title)}</h1><p class="lead">${esc(description)}</p></div>${extra}</div>`;
}
function refs(ids) {
  return ids
    .map((id) => state.platform.references.find((r) => r.id === id))
    .filter(Boolean)
    .map((r) => link(r.url, r.name + " ↗"))
    .join("<br>");
}
function docButton(id, title) {
  return `<button class="small" data-library="${esc(id)}">${esc(title)} ↗</button>`;
}
function renderWorkspace() {
  if (state.pageName === "markets") renderMarkets();
  else if (state.pageName === "cases") renderCases();
  else renderFoundation();
}
function renderFoundation() {
  const p = state.platform;
  const body = {
    overview: foundationOverview,
    methods: foundationMethods,
    agents: foundationAgents,
    knowledge: foundationKnowledge,
    review: foundationReview,
    roadmap: foundationRoadmap,
  }[state.foundationTab]();
  $("#content").innerHTML =
    pageHeader(
      "01 / Research foundations",
      "平台与研究基础",
      "先说明研究如何成立、如何被推翻，以及平台当前能做到什么。",
      tag("个人中长期研究 · 全球方法"),
    ) +
    `<nav class="tabs" aria-label="平台基础">${Object.entries(foundationTabs)
      .map(
        ([k, v]) =>
          `<button data-foundation-tab="${k}" class="${state.foundationTab === k ? "active" : ""}">${v}</button>`,
      )
      .join("")}</nav>` +
    body;
}
function foundationOverview() {
  const p = state.platform;
  return `<section class="card foundation-intro"><p class="eyebrow">A living research system</p><h2>方法持续迭代，判断保留依据。</h2><p>左侧三个方向连接为一条研究链：知识与方法 → 市场和公司原文 → 行业经营机制 → 财务观察、预测与估值 → 反方与报告更新。</p><p class="muted">知识参考可以增修并保留版本；信息源显示真实接入状态；公司报告记录采用的方法、事实、市场输入及前后变化。</p></section><div class="note section-gap"><strong>当前核心审查结论</strong><p>${esc(p.review.verdict)}</p>${docButton("review", "查看审查事实与未解决问题")}</div><section class="card section-gap"><div class="card-heading"><h2>从研究问题，到可追查的判断链</h2><button class="small" data-foundation-tab="methods">展开方法 →</button></div>${workflowStrip()}<p class="muted">每步保留输入、证据状态与未知；资料不够时补证或暂缓。输出是否有用，要看关键反证能否改变判断。</p></section><div class="grid section-gap">${p.capabilities.map((c) => `<section class="card capability"><div class="card-heading"><h3>${esc(c.name)}</h3>${tag(c.state, c.state.includes("未") ? "warn" : "neutral")}</div><p>${esc(c.detail)}</p></section>`).join("")}</div><section class="card section-gap"><h2>本平台参考什么</h2><p>借鉴投资思想中的企业经济性、资本回报与逆向审查；借鉴金融终端把数据、图表、研究和工作流连接起来的建设方式。各类原文的适用边界逐条保留。</p><div class="button-row"><button data-foundation-tab="knowledge">理论与文档 →</button><button data-page="markets">数据与大盘 →</button>${docButton("architecture", "完整三层方案")}</div></section>`;
}
function workflowStrip() {
  return `<ol class="workflow-strip">${state.platform.workflow.map((s) => `<li><span>${esc(s.id)}</span><strong>${esc(s.name)}</strong><small>${esc(s.output)}</small></li>`).join("")}</ol>`;
}
function foundationMethods() {
  const p = state.platform;
  return `<div class="grid">${p.principles.map((s) => `<article class="card"><h2>${esc(s.title)}</h2><p>${esc(s.detail)}</p><div class="reference-list">${refs(s.refs)}</div></article>`).join("")}<section class="card full"><h2>从问题到结论的十步工作流</h2><div class="workflow-list">${p.workflow.map((s) => `<div class="workflow-step"><span class="step-id">${esc(s.id)}</span><div><h3>${esc(s.name)}</h3><p>${esc(s.action)}</p><p class="muted">必须产出：${esc(s.output)}</p></div></div>`).join("")}</div></section><section class="card full"><h2>何时需要更多数据，何时停止</h2><div class="principles"><div><h3>优先区分解释</h3><p>先问下一份资料能否区分主假设与反方、翻转判断。原文已有但未提取时，先提取关键字段。</p></div><div><h3>关键矛盾先解决</h3><p>同期间同口径冲突、原件完整性失败或最新基线不可用时暂停相关模型。不能用较旧数字静默替代。</p></div><div><h3>保留未知与弃权</h3><p>缺乏经营机制、价格预期或资本约束，就限制对应结论。等待下一披露并登记什么会重新开启研究。</p></div></div><div class="button-row section-gap">${docButton("methodology", "完整研究方法")}${docButton("verification", "评价与验证标准")}</div></section></div>`;
}
function foundationAgents() {
  const p = state.platform;
  return `<div class="note"><strong>当前执行状态</strong><p>${esc(p.agent_execution.description)}</p></div><div class="grid section-gap">${p.agents.map((a, i) => `<article class="card"><p class="eyebrow">Role 0${i + 1} / ${esc(a.id)}</p><h2>${esc(a.name)}</h2><div class="key-line"><span>输入</span><div>${esc(a.inputs)}</div></div><div class="key-line"><span>输出</span><div>${esc(a.outputs)}</div></div><div class="key-line"><span>实现状态</span><div>${esc(a.current)}</div></div><p class="muted">约束：${esc(a.guard)}</p></article>`).join("")}<section class="card full"><h2>编排策略</h2><p>研究编排读取问题与旧结论，选择行业模板和来源；资料获取与核验分开；发现矛盾返回补证；建模读取适用事实与显式假设；反方可要求重算、补证或暂缓；报告保留依赖与版本。</p><p class="muted">接入模型后仍需逐步保存工具调用、引用和输入版本，验证补证相关性、最强反方与改判一致性。增加Agent数量不自动提高可信度。</p></section></div>`;
}
function foundationKnowledge() {
  const p = state.platform;
  return `<div class="knowledge-layers">${p.knowledge_layers.map((k, i) => `<section class="card"><span class="step-id">0${i + 1}</span><div><h3>${esc(k.name)}</h3><p>${esc(k.content)}</p><p class="meta">${esc(k.status)}</p></div></section>`).join("")}</div><section class="card section-gap"><h2>可打开的项目文档</h2><p class="muted">网站读取Repo中的文档原件，方法更新与功能验证一起进入Git。</p><div class="document-grid">${p.library.map((d) => `<button data-library="${esc(d.id)}"><strong>${esc(d.title)}</strong><span class="meta">${esc(d.path)}</span></button>`).join("")}</div></section><section class="card section-gap"><h2>理论、历史与建设参考</h2><div class="reference-cards">${p.references.map((r) => `<article><h3>${link(r.url, r.name + " ↗")}</h3><p>${esc(r.use)}</p></article>`).join("")}</div><p class="muted">这些资料用于构造问题、方法与审查条件；没有把作者的思想冒充成他们对当前六家公司的实际判断。</p></section>`;
}
function foundationReview() {
  const p = state.platform,
    q = p.verification;
  return `<div class="note"><strong>${esc(p.review.verdict)}</strong></div><div class="grid section-gap"><section class="card"><h2>审查发现</h2>${p.review.findings.map((f, i) => `<p class="finding"><b>0${i + 1}</b>${esc(f)}</p>`).join("")}${docButton("review", "逐项问题、反例与财务缺口")}</section><section class="card"><h2>验证证据状态</h2><div class="key-line"><span>功能检查</span><div>${q.functional_passed ? "上次运行通过" : "尚无通过记录"}</div></div><div class="key-line"><span>代码匹配</span><div>${q.evidence_current ? "报告摘要与当前文件匹配" : "实现已变化，等待本版重新验证"}</div></div><div class="key-line"><span>运行时间</span><div>${when(q.run_at)}</div></div><div class="key-line"><span>研究效果</span><div>尚未通过独立语义评价和前瞻校准</div></div><p class="muted">${esc(q.scope || "")}</p>${docButton("verification", "如何评价功能与研究质量")}</section><section class="card full"><h2>不能混用的四个通过条件</h2><div class="review-levels">${[
    ["功能与控制", "能运行、公式/版本/错误控制正确", "本地回归与反例"],
    ["资料与语义", "原文、口径、相关性、反方充分", "逐项原文裁定与专业复核"],
    [
      "研究方法",
      "经营驱动、资本约束与参数有依据",
      "独立计算、未见样本与替代解释",
    ],
    [
      "预测与决策",
      "超越简单基准、校准与风险效果",
      "预登记、前瞻结算、保留失败",
    ],
  ]
    .map(
      ([a, b, c]) =>
        `<article><h3>${a}</h3><p>${b}</p><small>${c}</small></article>`,
    )
    .join(
      "",
    )}</div></section><section class="card full"><h2>功能合同与下一验证</h2><div class="table-wrap"><table><thead><tr><th>功能</th><th>状态</th><th>通过门槛</th><th>下一项工作</th></tr></thead><tbody>${p.features.map((f) => `<tr><td><strong>${esc(f.id)}</strong><br>${esc(f.name)}</td><td>${tag(statusLabels[f.status] || f.status, "neutral")}</td><td>${esc(Array.isArray(f.acceptance) ? f.acceptance.join("；") : f.acceptance)}</td><td>${esc(Array.isArray(f.next_work) ? f.next_work.join("；") : f.next_work)}</td></tr>`).join("")}</tbody></table></div></section><section class="card full"><h2>效果评价的保留意见</h2>${p.review.limits.map((l) => `<p>• ${esc(l)}</p>`).join("")}</section></div>`;
}
function foundationRoadmap() {
  return `<div class="roadmap">${state.platform.roadmap.map((r, i) => `<section class="card"><span class="step-id">0${i + 1}</span><div><p class="eyebrow">${esc(r.stage)}</p><h2>${esc(r.goal)}</h2><p>${esc(r.work)}</p></div></section>`).join("")}</div><section class="card section-gap"><h2>每次扩展，先写清如何验收</h2><p>在Repo登记功能合同：帮助哪项决定、输入来源、观察/公开/取得时间、预期输出、失败方式和预写反例。完成后分别记录功能检查、原文语义与方法评价，以及尚未验证的部分。</p><p>新增公司：核证券身份和市场规则 → 选择或新建行业手册 → 核实际与KPI → 建经营和资本桥 → 暴露与情景 → 反方 → 条件报告。新增数据源：核定义、授权、时间、修订与缺失 → 小样本核对 → 失败与恢复 → 再扩覆盖。</p><div class="button-row">${docButton("feature_plan", "功能与验证计划")}${docButton("operations", "本地运行与部署依据")}</div></section>`;
}
function sparkline(points) {
  const valid = points.filter(
    (p) => p[1] != null && Number.isFinite(Number(p[1])),
  );
  if (valid.length < 2)
    return `<div class="spark-empty">仅 ${valid.length} 个有效观察 · 不能形成走势</div>`;
  const values = valid.map((p) => Number(p[1])),
    lo = Math.min(...values),
    hi = Math.max(...values),
    span = hi - lo || 1;
  let path = "",
    open = false;
  points.forEach((p, i) => {
    if (p[1] == null) {
      open = false;
      return;
    }
    const x = 4 + (i / (points.length - 1)) * 242,
      y = 44 - ((Number(p[1]) - lo) / span) * 36;
    path += `${open ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)} `;
    open = true;
  });
  return `<svg class="sparkline" viewBox="0 0 250 50" role="img" aria-label="按观察日排列的历史走势，缺失处断开"><path d="${path.trim()}" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>`;
}
function marketValue(m) {
  return m.value == null
    ? "尚无有效值"
    : Number(m.value).toLocaleString("zh-CN", { maximumFractionDigits: 4 });
}
function deltaLabel(m) {
  return m.change == null
    ? "无可比前值"
    : `${Number(m.change) > 0 ? "+" : ""}${m.change} ${m.change_unit}`;
}
function marketCard(m) {
  const failed = m.last_attempt?.status === "failed",
    manual = m.provenance?.mode === "manual_transcription";
  const stateLabel = {
    snapshot: manual ? "人工页面快照" : "公开延迟快照",
    derived: "同日数据派生",
    missing: "未取得序列",
    catalog: "来源目录 · 待接入",
    integrity_failed: "原件完整性失败",
  }[m.state];
  return `<article class="card market-card"><div class="card-heading"><h3>${esc(m.name)}</h3>${tag(m.region, "neutral")}</div><div class="market-number">${marketValue(m)}<small>${esc(m.unit)}</small></div><div class="market-change ${m.attention.triggered ? "attention" : ""}">${esc(deltaLabel(m))}${m.attention.triggered ? " · 触发关注条件" : ""}</div>${sparkline(m.history)}<div class="meta">观察 ${esc(m.date || "无")} ${m.age_days != null ? `· 距今 ${m.age_days} 天` : ""}<br>${esc(stateLabel)}${m.stale ? " · 超过目录时效条件" : ""}</div>${failed ? `<p class="source-failure">最近获取失败 · 旧观察日期保留</p>` : ""}<details><summary>定义、来源与数据边界</summary><p>${esc(m.definition)}</p><p class="muted">${esc(m.lag)}<br>有效观察 ${m.observations} 项；前一观察 ${esc(m.previous_date || "无")}。当日供应商数据可能仍是盘中观察。</p>${link(m.source_url, "来源页面 ↗")}${m.provenance ? `<p class="meta">取得 ${when(m.provenance.retrieved_at)}<br>${m.provenance.source_updated_at ? `来源更新 ${when(m.provenance.source_updated_at)}<br>` : ""}${esc(m.provenance.note || "")}<br>方式 ${esc(m.provenance.mode)}</p><div class="hash mono">SHA256 ${esc(m.provenance.sha256)}</div>` : ""}${m.inputs ? m.inputs.map((i) => `<p class="meta">${esc(i.id)} · ${esc(i.date || "缺失")} · ${i.last_attempt?.status === "failed" ? "最近获取失败" : "查看源卡片的取得时间与方式"}</p>`).join("") : ""}${failed ? `<p class="source-failure">${esc(m.last_attempt.error)} · ${when(m.last_attempt.created_at)}</p>` : ""}<p class="muted">关注阈值 ${esc(m.attention.threshold || "未设置")} ${esc(m.change_unit)}；${esc(m.attention.limit)}</p></details><button class="small channel-button" data-market-channel="${esc(m.id)}">查看行业传导 →</button></article>`;
}
function renderMarkets() {
  const m = state.markets;
  let body = "";
  if (state.marketTab === "information") body = informationView();
  else if (state.marketTab === "sources") body = sourceMap();
  else {
    const filtered = m.entries.filter(
      (e) =>
        (state.marketGroup === "all" || e.group === state.marketGroup) &&
        (state.marketRegion === "all" || e.region === state.marketRegion),
    );
    const jobs = m.jobs[0],
      busy = jobs && ["queued", "running"].includes(jobs.status);
    body = `<div class="kpis"><div class="kpi"><small>已有有效观察 / 含派生</small><strong>${m.observed}</strong></div><div class="kpi"><small>可尝试公开自动获取</small><strong>${m.automated_available}</strong></div><div class="kpi"><small>人工页面转录序列</small><strong>${m.manual_snapshots}</strong></div><div class="kpi"><small>仅目录 / 尚未接入</small><strong>${m.entries.filter((e) => e.state === "catalog").length}</strong></div></div><div class="note"><strong>看板状态：${esc(m.posture)}</strong><p>利率变化用基点，指数/汇率/商品用百分比，VIX用点。观察日、取得日和发布滞后分别展示；单点和缺失不补成完整曲线。当前未开启定时监控。</p></div><div class="board-tools section-gap"><div class="filter-row" aria-label="市场指标分组"><button data-market-group="all" class="${state.marketGroup === "all" ? "selected" : ""}">全部</button>${m.groups.map((g) => `<button data-market-group="${g.id}" class="${state.marketGroup === g.id ? "selected" : ""}">${esc(g.name)}</button>`).join("")}</div><div class="filter-row" aria-label="地区"><button data-market-region="all" class="${state.marketRegion === "all" ? "selected" : ""}">全球总览</button>${["美国", "香港", "中国", "全球"].map((r) => `<button data-market-region="${r}" class="${state.marketRegion === r ? "selected" : ""}">${r}</button>`).join("")}</div><div class="button-row"><button class="primary" id="refresh-markets" ${busy ? "disabled" : ""}>${busy ? "正在获取公开序列…" : "获取最新公开快照"}</button><button id="read-markets">读取任务状态 ↻</button><span class="meta">${jobs ? `最近任务：${esc(jobs.status)} · ${when(jobs.updated_at)}` : "尚无应用取数任务"}</span></div>${jobs?.error ? `<p class="source-failure">${esc(jobs.error)}。失败源保留旧快照及原观察日。</p>` : ""}</div>${marketChannelPanel()}<div class="market-grid section-gap">${filtered.map(marketCard).join("") || empty("该筛选暂无序列；这不代表市场没有风险。")}</div><section class="card section-gap"><h2>如何把市场变化用于研究</h2>${m.interpretation.map((t, i) => `<p><b>0${i + 1}</b>　${esc(t)}</p>`).join("")}${docButton("markets", "市场框架与来源验收")}</section>`;
  }
  $("#content").innerHTML =
    pageHeader(
      "02 / Markets & information",
      "市场与信息看板",
      "观察大盘和经济环境；沿暴露、时滞与资本约束，追到行业和公司。",
    ) +
    `<nav class="tabs" aria-label="市场看板"><button data-market-tab="board" class="${state.marketTab === "board" ? "active" : ""}">大盘与关键变量</button><button data-market-tab="sources" class="${state.marketTab === "sources" ? "active" : ""}">信息源与覆盖</button><button data-market-tab="information" class="${state.marketTab === "information" ? "active" : ""}">公告与政策信息</button></nav>` +
    body;
}
function marketChannelPanel() {
  if (!state.marketChannel) return "";
  const metric = state.markets.entries.find(
    (m) => m.id === state.marketChannel,
  );
  const industries = state.industries.industries.filter((i) =>
    i.macro.includes(metric.id),
  );
  return `<section class="card transmission-panel section-gap"><div class="card-heading"><h2>${esc(metric.name)} → 行业 → 公司</h2><button class="small" id="clear-market-channel">收起 ×</button></div><p class="muted">${esc(metric.date || "尚无观察")} · ${marketValue(metric)} ${esc(metric.unit)} · ${esc(deltaLabel(metric))}。以下为研究机制，未测算个股利润或估值变动。</p>${industries.map((i) => `<div class="key-line"><span><button class="small" data-industry="${i.id}">${esc(i.name)} →</button></span><div>${esc(i.channels.find((c) => c[0] === metric.id)?.[1] || "背景相关变量；先确定公司业务、资产/负债和预期暴露，再设定净影响及反证。")}</div></div>`).join("") || "<p>当前六类行业尚未建立此变量的具体暴露映射。保留为背景信息，下一步按研究问题扩展。</p>"}</section>`;
}
function sourceMap() {
  return `<div class="note">先确定要回答的问题，再选拥有原始证据的来源。来源目录、一次读取、字段核验和持续覆盖是四种不同状态。</div><section class="card section-gap"><h2>核心来源地图</h2><div class="table-wrap"><table><thead><tr><th>来源</th><th>用于哪项判断</th><th>市场 / 频率</th><th>当前覆盖与缺口</th></tr></thead><tbody>${state.platform.sources.map((s) => `<tr><td>${link(s.url, s.name + " ↗")}</td><td>${esc(s.purpose)}</td><td>${esc(s.region)}<br>${esc(s.frequency)}</td><td>${esc(s.status)}</td></tr>`).join("")}</tbody></table></div></section><section class="card section-gap"><h2>看板序列的真实可得性</h2><div class="table-wrap"><table><thead><tr><th>指标 / 提供路径</th><th>观察与取得</th><th>最近状态</th><th>关键限制</th></tr></thead><tbody>${state.markets.entries.map((m) => `<tr><td>${link(m.source_url, m.name + " ↗")}<div class="meta">${esc(m.provider)}</div></td><td>${esc(m.date || "未取得")}<br><span class="meta">${m.provenance ? when(m.provenance.retrieved_at) : m.provider === "derived" ? "见输入序列" : "目录入口"}</span></td><td>${esc(m.last_attempt?.status || m.state)}${m.last_attempt?.error ? `<p class="source-failure">${esc(m.last_attempt.error)}</p>` : ""}</td><td>${esc(m.lag)}</td></tr>`).join("")}</tbody></table></div><div class="button-row section-gap">${docButton("sources", "完整数据源文档")}${docButton("markets", "定义、缺失与更新合同")}</div></section>`;
}
function researchPublications() {
  const p = state.platform.research_publications;
  if (!p?.publications?.length) return "";
  return `<section class="card section-gap"><div class="card-heading"><h2>专题深度研究 · ${esc(p.as_of)}</h2>${tag("有日期的研究版本 · 未评级", "neutral")}</div><p class="muted">原文证据、盈利与现金传导、定价条件、反方与下一验证。价格参考 ${esc(p.price_as_of)}；后续新证据应形成新版本。</p><div class="industry-grid">${p.publications.map(r=>`<article class="industry-card"><h3>${esc(r.title)}</h3><p>${esc(r.description)}</p><a class="primary" href="${esc(r.route)}" target="_blank" rel="noopener">阅读完整专题报告 ↗</a></article>`).join("")}</div></section>`;
}
function renderCases() {
  const d = state.industries;
  const filtered = d.industries.filter(
    (i) =>
      (state.industryGroup === "all" || i.group === state.industryGroup) &&
      (!state.industryId || i.id === state.industryId),
  );
  $("#content").innerHTML =
    pageHeader(
      "03 / Industries & company research",
      "行业与公司研究",
      "先选择经济机制与行业指标，再把方法应用到公司。每份报告连接事实、假设、反方与下一验证。",
    ) +
    researchPublications() +
    `<div class="note"><strong>行业分类口径</strong><p>${esc(d.classification)}</p>现阶段已有行业手册和报告结构，六家经营到预测的驱动模型仍待逐项完成。</div><div class="filter-row section-gap"><button data-industry-group="all" class="${state.industryGroup === "all" && !state.industryId ? "selected" : ""}">全部行业 · 六家公司</button>${d.groups.map((g) => `<button data-industry-group="${g.id}" class="${state.industryGroup === g.id ? "selected" : ""}">${esc(g.name)}</button>`).join("")}</div><div class="industry-grid section-gap">${filtered
      .map(
        (i) =>
          `<section class="card industry-card"><div class="card-heading"><h2>${esc(i.name)}</h2>${tag(d.groups.find((g) => g.id === i.group).name, "neutral")}</div><p class="question">${esc(i.question)}</p><p class="muted">${esc(i.structure)}</p><h3>关键行业指标</h3><div class="kpi-tags">${i.kpis.map((k) => tag(k, "neutral")).join("")}</div><h3 class="section-gap">经营 → 利润 → 现金与资本</h3><p>${esc(i.bridge)}</p><details><summary>估值、反方与下一验证</summary><p><strong>估值方法：</strong>${esc(i.valuation)}</p><p><strong>最强反方：</strong>${esc(i.opposition)}</p><p><strong>下一验证：</strong>${esc(i.verification)}</p><div class="reference-list">${refs(i.refs)}</div></details><div class="macro-chips">${i.macro.map((id) => `<button class="small" data-to-market="${id}">${esc(state.markets.entries.find((m) => m.id === id).name)}</button>`).join("")}</div>${i.companies
            .map((id) => {
              const c = state.companies.find((c) => c.id === id);
              return `<div class="industry-company"><div><strong>${esc(c.name)}</strong><div class="meta">${esc(c.market)} · ${c.documents}份原文 · ${c.verified}项局部核验</div>${tag(c.conclusion?.stale ? "旧结论待复核" : "研究草案 · 未通过效果验收", "warn")}</div><button class="primary" data-company="${id}">阅读研究报告 →</button></div>`;
            })
            .join("")}</section>`,
      )
      .join(
        "",
      )}</div><section class="card section-gap"><h2>所有报告使用同一份输出合同</h2><div class="report-contract">${d.report_sections.map((s, i) => `<span><b>${String(i + 1).padStart(2, "0")}</b> ${esc(s)}</span>`).join("")}</div><p class="muted">统一的是证据和判断纪律；财务驱动与估值方法随行业变化。报告保留当前模型限制和未知，不以空泛的正面/负面观点代替分析。</p>${docButton("industries", "行业研究与报告合同")}</section>`;
}
function reportView() {
  const r = state.report,
    c = r.conclusion,
    m = r.model,
    i = r.industry;
  return `<div class="report-toolbar"><span class="meta">报告草案 · ${esc(i.name)} · 组合生成 ${when(r.generated_at)}</span><button class="small" id="export-report">导出结构化报告 ↗</button></div><div class="note"><strong>摘要与允许用途</strong><p>${esc(r.hypothesis.question)}</p><p>${r.needs_review ? "研究结论缺失或依赖变化，需重新审查。" : "已有条件结论记录。"} 当前未通过研究决策质量验收；示例估值不能视为当前公允价值或交易指令。</p></div><div class="grid section-gap"><section class="card"><h2>行业与业务机制</h2><p>${esc(i.structure)}</p><h3>行业指标</h3><div class="kpi-tags">${i.kpis.map((k) => tag(k, "neutral")).join("")}</div><h3 class="section-gap">经营到财务</h3><p>${esc(i.bridge)}</p><p class="muted">${esc(i.valuation)}</p><div class="reference-list">研究方法依据：<br>${refs(i.refs)}</div></section><section class="card"><h2>主判断与竞争解释</h2><div class="key-line"><span>主假设</span><div>${esc(r.hypothesis.thesis)}</div></div><div class="key-line"><span>替代解释</span><div>${esc(r.hypothesis.counter_thesis)}</div></div><div class="key-line"><span>当前传导</span><div>${esc(r.hypothesis.transmission)}</div></div><p class="muted">以上仍是待证假设；行业反方：${esc(i.opposition)}</p><button class="small" data-tab="overview">修改研究问题与假设 →</button></section><section class="card full"><div class="card-heading"><h2>已核验事实与财务质量</h2><button class="small" data-tab="evidence">完整事实、原页与口径 →</button></div><p class="muted">${r.evidence.documents}份原文 · ${r.evidence.verified}项局部核验 · ${r.evidence.candidates}项候选 · ${r.evidence.conflicts}组冲突。下表按指标/口径展示最新可用观察；期间长短不同，不能直接横比。</p><div class="table-wrap"><table><thead><tr><th>指标 / 会计口径</th><th>观察期间</th><th class="number">数值 / 单位</th><th>证据</th></tr></thead><tbody>${r.financials.map((f) => `<tr><td>${esc(f.label)}<div class="meta">${esc(f.basis)} / ${esc(f.scope)}</div></td><td class="mono">${esc(f.period_start || "时点")}<br>${esc(f.period_end)}</td><td class="number mono">${fmt(f.value, f.unit === "ratio")}<div class="meta">${esc(f.unit)}</div></td><td><button class="small" data-doc="${esc(f.document_id)}" data-source-page="${sourcePage(f.locator)}">${esc(f.locator)} ↗</button></td></tr>`).join("")}</tbody></table></div></section>${monitorCards(r.monitors)}<section class="card full"><div class="card-heading"><h2>市场变量与行业传导</h2><button class="small" data-page="markets">完整大盘看板 →</button></div>${r.macro_channels.map((ch) => `<article class="macro-report"><div><strong>${esc(ch.observation.name)}</strong><p class="mono">${marketValue(ch.observation)} ${esc(ch.observation.unit)} · ${esc(ch.observation.date || "未接入")}<br>${esc(deltaLabel(ch.observation))}</p>${ch.observation.last_attempt?.status === "failed" ? tag("最近获取失败 · 旧快照", "warn") : ""}</div><div><p>${esc(ch.mechanism)}</p><p class="muted">${esc(ch.posture)}</p></div></article>`).join("")}<p class="muted">${esc(r.context_note)}</p></section><section class="card"><h2>盈利、估值与预期</h2><p>当前模型：${esc(m ? { bank_residual_income: "银行普通股剩余收益示例", earnings_scenario: "盈利与分配情景示例" }[m.model_type] || "示例模型" : "尚未运行")}。${m?.stale ? "模型依赖已变化，需要重算。" : ""}</p><p>${m ? "已保存确定性示例情景；尚未完成本行业的经营驱动、资本与融资约束及参数承保。" : "建立经营驱动及资本桥前，不产出当前公允价值。"}</p><p class="muted">尚无经时点核对的当前证券价格与完整共识，不能判断已被价格反映的程度。</p><button class="small" data-tab="models">查看模型输入、公式与情景 →</button></section><section class="card"><h2>反方与联合压力</h2><p>${esc(i.opposition)}</p><p>${esc(i.verification)}</p><p class="muted">检查需求下滑、利润率收缩、融资收紧和估值压缩同时发生的路径。下行情景不是最大损失上限。</p><button class="small" data-tab="review">查看/更新反方复核 →</button></section>${c ? conclusionCard(c) : `<section class="card"><h2>条件结论</h2><p>尚无已发布的条件结论。先完成模型与反方复核。</p><button data-tab="conclusion">进入结论记录 →</button></section>`}<section class="card"><h2>可信度按层表达</h2>${Object.entries(
    {
      事实: r.confidence.facts,
      经营解释: r.confidence.mechanism,
      估值预测: r.confidence.valuation,
      概率: r.confidence.calibration,
    },
  )
    .map(
      ([k, v]) =>
        `<div class="key-line"><span>${k}</span><div>${esc(v)}</div></div>`,
    )
    .join(
      "",
    )}</section><section class="card full"><h2>这家公司如何应用工作流</h2><div class="workflow-application">${r.workflow_application.map((s) => `<article><h3>${esc(s.step)}</h3><p>${esc(s.result)}</p><button class="small" data-tab="${s.tab}">查看研究记录 →</button></article>`).join("")}</div></section><section class="card full"><h2>下一补证与更新条件</h2>${r.gaps.map((g) => `<div class="task"><h3>${esc(g.title)}</h3><p>${esc(g.why)}</p><p class="muted">${esc(g.next_source)} · ${esc(g.blocks)}</p></div>`).join("")}<button class="primary" data-tab="gaps">安排补证或记录停止理由 →</button><p class="meta section-gap">公司修订 ${r.revision} · 背景摘要 ${esc(r.context_digest.slice(0, 16))} · 草案与历史结论分开保留</p></section></div>`;
}
function downloadJSON(value, filename) {
  const blob = new Blob([JSON.stringify(value, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function handleWorkspaceClick(b) {
  if (b.dataset.page) {
    state.id = null;
    state.pageName = b.dataset.page;
    renderNav();
    renderWorkspace();
    window.scrollTo(0, 0);
  } else if (b.dataset.foundationTab) {
    state.foundationTab = b.dataset.foundationTab;
    renderFoundation();
  } else if (b.dataset.library) {
    const d = await api(
      "/api/library/" + encodeURIComponent(b.dataset.library),
    );
    $("#library-title").textContent = d.title;
    $("#library-path").textContent = d.path;
    $("#library-text").textContent = d.text;
    $("#library-dialog").showModal();
  } else if (b.id === "close-library") $("#library-dialog").close();
  else if (b.dataset.marketTab) {
    state.marketTab = b.dataset.marketTab;
    renderMarkets();
  } else if (b.dataset.marketGroup) {
    state.marketGroup = b.dataset.marketGroup;
    renderMarkets();
  } else if (b.dataset.marketRegion) {
    state.marketRegion = b.dataset.marketRegion;
    renderMarkets();
  } else if (b.dataset.marketChannel) {
    state.marketChannel = b.dataset.marketChannel;
    renderMarkets();
    $(".transmission-panel").scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  } else if (b.id === "clear-market-channel") {
    state.marketChannel = null;
    renderMarkets();
  } else if (b.id === "refresh-markets") {
    await api("/api/markets/refresh", {});
    state.markets = await api("/api/markets");
    renderMarkets();
    toast("公开获取任务已入队；失败源保留旧观察。稍后读取任务状态。");
  } else if (b.id === "read-markets") {
    state.markets = await api("/api/markets");
    renderMarkets();
    toast("已读取来源与任务状态");
  } else if (b.dataset.industryGroup) {
    state.industryGroup = b.dataset.industryGroup;
    state.industryId = null;
    renderCases();
  } else if (b.dataset.industry) {
    state.id = null;
    state.pageName = "cases";
    state.industryId = b.dataset.industry;
    state.industryGroup = "all";
    renderNav();
    renderCases();
    window.scrollTo(0, 0);
  } else if (b.dataset.toMarket) {
    state.id = null;
    state.pageName = "markets";
    state.marketTab = "board";
    state.marketGroup = "all";
    state.marketRegion = "all";
    state.marketChannel = b.dataset.toMarket;
    renderNav();
    renderMarkets();
    window.scrollTo(0, 0);
  } else if (b.id === "export-report")
    downloadJSON(
      await api("/api/reports/" + state.id),
      `pfa-report-${state.id}-${new Date().toISOString().slice(0, 10)}.json`,
    );
  else return false;
  return true;
}
