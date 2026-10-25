"use strict";
const originalKnowledgeView = foundationKnowledge;
foundationKnowledge = function () {
  return knowledgeWorkbench() + originalKnowledgeView();
};
const originalReportView = reportView;
reportView = function () {
  return (
    researchReportCore() +
    `<details class="report-appendix"><summary>展开完整行业背景、原文表、历史结论及操作附录</summary>${originalReportView()}</details>`
  );
};
const knowledgeStatuses = {
  draft: "待审议草案",
  adopted: "已纳入本地参考",
  retired: "已停用",
};
function scopeLabel(scope) {
  if (scope === "all") return "全局";
  if (scope === "platform") return "平台建设";
  const [type, id] = scope.split(":");
  return type === "issuer"
    ? state.companies.find((c) => c.id === id)?.name || id
    : state.industries.industries.find((i) => i.id === id)?.name || id;
}
function knowledgeWorkbench() {
  const k = state.knowledge;
  return `<section class="card"><div class="card-heading"><div><p class="eyebrow">Versioned knowledge</p><h2>可以持续维护的研究方法库</h2></div><button class="primary" id="new-knowledge">新增知识或方法</button></div><p>记录来源、适用范围、采用条件与失效条件。修订另存新版本，报告保留其采用的方法版本；草案不会替换已采用版本。</p><p class="muted">${esc(k.adoption_meaning)}</p></section>${state.knowledgeEdit ? knowledgeEditor() : ""}<div class="method-inventory section-gap">${k.entries
    .map((e) => {
      const r = e.latest;
      return `<article class="card"><details><summary>${esc(r.title)}</summary><p>${esc(r.content)}</p><p class="muted">适用：${r.applies_to.map(scopeLabel).map(esc).join("、")}<br>条件/失效：${esc(r.falsifier)}</p>${link(r.source_url, "来源原文 ↗")}<h3 class="section-gap">版本记录</h3>${e.history.map((v) => `<p class="meta">v${v.version} · ${esc(knowledgeStatuses[v.status])} · ${esc(v.change_reason)}</p>`).join("")}</details><div class="meta">最新 v${r.version} · ${esc(knowledgeStatuses[r.status])}${e.active ? ` / 报告采用 v${e.active.version}` : " / 尚无采用版本"}</div><button class="small" data-edit-knowledge="${esc(e.entry_id)}">修订并保留旧版 →</button></article>`;
    })
    .join("")}</div>`;
}
function knowledgeEditor() {
  const entry = state.knowledge.entries.find(
      (e) => e.entry_id === state.knowledgeEdit,
    ),
    r = entry?.latest || {
      status: "draft",
      category: "method",
      applies_to: ["all"],
    };
  const scopes = [
    ["all", "全局"],
    ["platform", "平台建设"],
    ...state.companies.map((c) => ["issuer:" + c.id, c.name]),
    ...state.industries.industries.map((i) => ["industry:" + i.id, i.name]),
  ];
  return `<section class="card knowledge-editor"><h2>${entry ? "修订方法 · 保留历史" : "新增研究知识"}</h2><form data-form="knowledge"><input type="hidden" name="entry_id" value="${esc(entry?.entry_id || "")}"><input type="hidden" name="expected_version" value="${r.version || 0}"><div class="form-grid"><label class="wide"><span>标题</span><input name="title" required minlength="3" maxlength="180" value="${esc(r.title || "")}"></label><label><span>知识类型</span><select name="category">${Object.entries(
    state.knowledge.categories,
  )
    .map(
      ([id, title]) =>
        `<option value="${id}" ${r.category === id ? "selected" : ""}>${title}</option>`,
    )
    .join(
      "",
    )}</select></label><label><span>本地状态</span><select name="status">${Object.entries(
    knowledgeStatuses,
  )
    .map(
      ([id, title]) =>
        `<option value="${id}" ${r.status === id ? "selected" : ""}>${title}</option>`,
    )
    .join(
      "",
    )}</select></label><label class="wide"><span>原始来源（采用版本需要HTTPS原文）</span><input name="source_url" type="url" value="${esc(r.source_url || "")}" placeholder="https://…"></label><label class="wide"><span>方法、知识及使用办法</span><textarea name="content" minlength="12" maxlength="16000" required>${esc(r.content || "")}</textarea></label><label class="wide"><span>适用/失效条件：什么情况下应暂停或改用其他方法</span><textarea name="falsifier">${esc(r.falsifier || "")}</textarea></label><label class="wide"><span>适用范围，可多选；选择全局将适用于所有研究</span><select name="applies_to" multiple size="5">${scopes.map(([id, title]) => `<option value="${esc(id)}" ${r.applies_to.includes(id) ? "selected" : ""}>${esc(title)}</option>`).join("")}</select></label><label class="wide"><span>本次改变什么、为什么改变</span><textarea name="change_reason" required minlength="12" placeholder="保留修改依据与尚需检验的部分"></textarea></label></div><div class="button-row"><button class="primary">保存新版本</button><button type="button" id="cancel-knowledge">取消编辑</button><span class="muted">纳入本地参考不代表方法已经获得专业验证。</span></div></form></section>`;
}
function informationView() {
  const data = state.information,
    job = data.jobs[0],
    busy = job && ["queued", "running"].includes(job.status);
  return `<div class="delivery-strip"><strong>当前接入：公开数据按需获取</strong><br>${esc(data.delivery.explanation)}<br>${esc(data.delivery.missing)}</div><div class="card"><div class="card-heading"><h2>公告与政策信息流</h2><div class="button-row"><button id="refresh-information" class="primary" ${busy ? "disabled" : ""}>${busy ? "正在获取公开信息…" : "获取最新公告线索"}</button><button id="read-information">读取任务状态 ↻</button></div></div><p class="muted">当前仅选定SEC公司提交记录和美联储RSS。标题、提交日期与正文核验分别处理，不自动生成利好/利空或盈利修订。</p><p class="meta">${job ? `最近任务：${esc(job.status)} · ${when(job.updated_at)}` : "尚无公开信息任务"}${job?.error ? " · " + esc(job.error) : ""}</p></div><div class="information-sources section-gap">${data.sources.map((s) => `<section class="card"><h3>${esc(s.name)}</h3><p class="meta">${esc(s.coverage)}</p><p>${s.last_attempt ? esc(s.last_attempt.status) : "尚未获取"}</p><p class="meta">${s.last_attempt ? when(s.last_attempt.retrieved_at) : ""}</p>${s.last_attempt?.error ? `<p class="source-failure">${esc(s.last_attempt.error)}</p>` : ""}${link(s.url, "源接口 ↗")}</section>`).join("")}</div>${state.informationLink ? informationLinkForm() : ""}<div class="information-items section-gap">${data.items.map((i) => `<article class="card information-item"><div class="card-heading"><h3>${link(i.url, i.title + " ↗")}</h3>${tag(i.verification === "unreviewed_metadata" ? "元数据 · 正文待审" : "原件不可核", "warn")}</div><p class="meta">公开 ${when(i.published_at)} · 首次取得 ${when(i.first_seen_at)} · ${esc(i.source_id)}</p><p class="muted">${i.issuer === "_macro" ? "宏观/政策背景，需先判断与公司的具体关联。" : "公司提交记录；较新公告会提示研究报告回看，不自动变成已核验财务。"}</p><button class="small" data-link-information="${esc(i.id)}" ${i.verification !== "unreviewed_metadata" ? "disabled" : ""}>关联到公司研究 →</button></article>`).join("") || empty("尚无已取得的信息。可发起公开读取；没有消息不代表没有事件。")}</div>`;
}
function informationLinkForm() {
  const item = state.information.items.find(
    (i) => i.id === state.informationLink,
  );
  return `<section class="card section-gap"><h2>把线索转为待核查研究事件</h2><p>${esc(item.title)}</p><form data-form="information-link"><input name="information_id" type="hidden" value="${esc(item.id)}"><label><span>关联公司</span><select name="issuer">${state.companies.map((c) => `<option value="${c.id}" ${item.issuer === c.id ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select></label><label><span>暴露→经营/财务通道：为什么与这家公司相关</span><textarea name="mechanism" required minlength="12"></textarea></label><label><span>还缺什么证据，哪些不能从标题推断</span><textarea name="unknown" required minlength="12"></textarea></label><label><span>下一验证和重开条件</span><textarea name="next_validation" required minlength="12"></textarea></label><div class="button-row"><button class="primary">登记待核查事件</button><button type="button" id="cancel-information-link">取消</button></div><p class="muted">会触发公司原结论重新复核，不会自动核验公告或改写盈利参数。</p></form></section>`;
}
function researchReportCore() {
  const r = state.report,
    s = r.report_summary,
    g = r.valuation_gate,
    d = r.report_delta,
    b = state.platform.report_benchmarks;
  return `<section class="card report-lead"><p class="eyebrow">Evidence-led research update</p><div class="card-heading"><h2>核心研究报告 · 证据与判断</h2>${tag("研究更新草案 · 未评级", "warn")}</div><p class="question">${esc(r.hypothesis.question)}</p><p class="meta">公司原文公开截止 ${esc(s.fact_cutoff || "未确认")} · 市场逐项注明观察日 · 方法逐项注明版本</p><p>${esc(s.input_note)}</p><div class="button-row"><a class="report-open" href="/reports/${encodeURIComponent(r.company.id)}" target="_blank" rel="noopener">打开独立报告 ↗</a><button class="small" id="download-report">下载 HTML ↗</button><button class="small" id="show-report-snapshot">保存本轮研究快照</button>${docButton("benchmark", "公开机构报告对照")}</div></section><div class="report-kpis"><section><h3>经营方向</h3><strong>${esc(s.business_label)}</strong></section><section><h3>现金与资本</h3><strong>${esc(s.cash_label)}</strong></section><section><h3>证券经济性</h3><strong>${esc(s.pricing_label)}</strong></section></div>${d.changed_domains.length ? `<section class="dependency-delta"><strong>相对已存 v${d.previous_version}，报告依赖发生变化</strong><p>${d.reasons.map(esc).join("；")}。请复核哪些判断需要改变，再保存新稿。旧版仍可查看。</p></section>` : `<p class="meta">${d.previous_version ? `已存 v${d.previous_version} · 本轮经济输入未变化` : "尚无已存报告版本。可保存当前草案建立更新基线。"} · ${when(r.generated_at)}</p>`}${state.showReportSnapshot ? `<section class="card section-gap"><h2>保存研究草案快照</h2><form data-form="report-snapshot"><label><span>本轮发生什么变化，结论为何保留/修订，哪些仍未解决</span><textarea name="reason" required minlength="12"></textarea></label><label><span>保存用途</span><select name="actor"><option value="local_researcher">研究者保存草案</option><option value="implementation_acceptance">助手整理/开发验收，尚未经本人独立复核</option></select></label><button class="primary">保存新稿，保留旧版</button></form><p class="muted">保存只是留存本轮研究，不会解除估值门槛或升级为正式投资评级。</p></section>` : ""}<div class="report-findings section-gap">${
    r.findings
      .map(
        (f) =>
          `<section class="card report-finding ${f.kind === "monitor" ? "critical" : ""}"><p class="eyebrow">${f.kind === "monitor" ? "Cash & risk / 重点复核" : "Reported observation / 已报观察"}</p><h2>${esc(f.title)}</h2><p>${esc(f.observation)}</p>${f.formula ? `<div class="formula">${esc(f.formula)}</div>` : ""}<div class="key-line"><span>经营通道</span><div>${esc(f.transmission)}</div></div><div class="key-line"><span>财务影响</span><div>${esc(f.financial_effect)}</div></div><div class="key-line"><span>估值影响</span><div>${esc(f.valuation_effect)}</div></div><div class="key-line"><span>最强反方</span><div>${esc(f.counter)}</div></div><div class="key-line"><span>下一证据</span><div>${esc(f.next_evidence)}</div></div><h3 class="section-gap">这条判断读取了哪些证据</h3><div class="evidence-links">${f.fact_ids
            .map((id) => r.evidence_map[id])
            .filter(Boolean)
            .map(
              (f) =>
                `<button class="small" data-doc="${esc(f.document_id)}" data-source-page="${sourcePage(f.locator)}">${esc(f.label)} · ${esc(f.period_end)} · ${esc(f.locator)} ↗</button>`,
            )
            .join("")}</div><p class="meta">方法：${f.methods
            .map((id) => r.methods_applied.find((m) => m.entry_id === id))
            .filter(Boolean)
            .map((m) => `${esc(m.title)} v${m.version}`)
            .join("；")}</p></section>`,
      )
      .join("") ||
    empty("适用可比观察尚不足。不能用通用描述补成确定的经营方向。")
  }</div><div class="grid section-gap"><section class="card full"><h2>经营、现金与资本的实际输入</h2><p class="muted">下表为各指标最新可用观察；报告期、单位和口径分别列明，不把中期年度化或不同期间直接横比。</p><div class="table-wrap"><table><thead><tr><th>指标 / 口径</th><th>观察期间</th><th class="number">报告值 / 单位</th><th>原文</th></tr></thead><tbody>${r.financials.map((f) => `<tr><td>${esc(f.label)}<div class="meta">${esc(f.basis)} / ${esc(f.scope)}</div></td><td class="mono">${esc(f.period_start || "时点")}<br>${esc(f.period_end)}</td><td class="number mono">${fmt(f.value, f.unit === "ratio")}<div class="meta">${esc(f.unit)}</div></td><td><button class="small" data-doc="${esc(f.document_id)}" data-source-page="${sourcePage(f.locator)}">${esc(f.locator)} ↗</button></td></tr>`).join("")}</tbody></table></div></section><section class="card full"><h2>预测与估值：哪些条件还不具备</h2><p>当前输出为证据研究更新。个股经营/资本预测、现价和预期资料未完成前，不生成目标价或买卖评级。</p><div class="gate-list">${g.checks.map((c) => `<div class="gate-row"><span>${esc(c.name)}</span>${tag(c.passed ? "本轮局部满足" : "待完成", c.passed ? "neutral" : "warn")}</div>`).join("")}</div><p class="muted">门槛满足不能替代专业语义与前瞻验证；当前研究决策状态仍为未通过。</p></section><section class="card full"><div class="card-heading"><h2>市场与事件怎样影响本稿</h2><button class="small" data-to-information="true">查看公告与政策信息 →</button></div>${r.macro_channels.map((ch) => `<div class="key-line"><span>${esc(ch.observation.name)}<small class="meta">${esc(ch.observation.date || "未接入")}</small></span><div>${marketValue(ch.observation)} ${esc(ch.observation.unit)} · ${esc(ch.mechanism)}<p class="muted">${esc(ch.posture)}</p></div></div>`).join("")}<h3 class="section-gap">较新公司披露，正文/财务尚待核验 ${r.pending_disclosures.length}</h3>${
    r.pending_disclosures
      .slice(0, 8)
      .map(
        (i) =>
          `<p>${esc(i.published_at.slice(0, 10))} · ${link(i.url, i.title + " ↗")}</p>`,
      )
      .join("") ||
    '<p class="muted">当前接入范围内未发现比原文台账更晚的提交；完整港A/新闻覆盖尚未建立。</p>'
  }${r.events.map((e) => `<div class="task"><h3>${esc(e.title)}</h3><p>${esc(e.mechanism)}</p><p class="muted">未知：${esc(e.unknown)}<br>下一验证：${esc(e.next_validation)}</p>${link(e.source_url, "事件原文 ↗")}</div>`).join("")}</section><section class="card full"><h2>本稿引用的方法与适用边界</h2><div class="reference-cards">${r.methods_applied.map((m) => `<article><h3>${link(m.source_url, m.title + " ↗")} <small>v${m.version}</small></h3><p>${esc(m.content)}</p><small>边界：${esc(m.falsifier)}</small></article>`).join("")}</div><p class="muted">方法引用、历史事实、解释充分性与预测效果分别验证。修改方法会标记已存报告重新检查。</p></section><section class="card full"><h2>报告版本与修订原因</h2>${r.report_history.map((v) => `<div class="key-line"><span>v${v.version}</span><div>${esc(v.reason)}<p class="meta">${when(v.created_at)} · ${esc(v.dependency_digest.slice(0, 16))}</p><button class="small" data-report-version="${esc(v.id)}">下载该版报告 ↗</button></div></div>`).join("") || '<p class="muted">尚无已存版本。</p>'}</section><section class="card full"><h2>对照机构研究，接下来补什么</h2><p>本稿已把事实、方法版本、市场背景和修订理由连接。仍需把行业驱动写入预测、交叉估值并完成独立反方审议。</p>${b.priorities.map((p) => `<p><strong>${esc(p.stage)}</strong> · ${esc(p.item)}</p>`).join("")}<div class="button-row">${docButton("report_design", "报告内核与迭代设计")}${docButton("benchmark", "公开研究样本与采用边界")}</div></section></div>`;
}
function downloadHTML(html, name) {
  const blob = new Blob([html], { type: "text/html;charset=utf-8" }),
    url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function handleEvolutionClick(b) {
  if (b.id === "new-knowledge") {
    state.knowledgeEdit = "new";
    renderFoundation();
    $(".knowledge-editor").scrollIntoView({ behavior: "smooth" });
  } else if (b.dataset.editKnowledge) {
    state.knowledgeEdit = b.dataset.editKnowledge;
    renderFoundation();
    $(".knowledge-editor").scrollIntoView({ behavior: "smooth" });
  } else if (b.id === "cancel-knowledge") {
    state.knowledgeEdit = null;
    renderFoundation();
  } else if (b.id === "refresh-information") {
    await api("/api/information/refresh", {});
    state.information = await api("/api/information");
    renderMarkets();
    toast("信息获取已入队；取得线索后仍需阅读原文。");
  } else if (b.id === "read-information") {
    state.information = await api("/api/information");
    renderMarkets();
    toast("已读取公开信息与来源状态");
  } else if (b.dataset.linkInformation) {
    state.informationLink = b.dataset.linkInformation;
    renderMarkets();
    $('form[data-form="information-link"]').scrollIntoView({
      behavior: "smooth",
    });
  } else if (b.id === "cancel-information-link") {
    state.informationLink = null;
    renderMarkets();
  } else if (b.dataset.toInformation) {
    state.id = null;
    state.pageName = "markets";
    state.marketTab = "information";
    renderNav();
    renderMarkets();
    window.scrollTo(0, 0);
  } else if (b.id === "show-report-snapshot") {
    state.showReportSnapshot = !state.showReportSnapshot;
    renderCompany();
  } else if (b.id === "download-report") {
    const d = await api("/api/reports/" + state.id + "/document");
    downloadHTML(d.html, `pfa-research-${state.id}.html`);
  } else if (b.dataset.reportVersion) {
    const d = await api("/api/report-versions/" + b.dataset.reportVersion);
    downloadHTML(d.html, `pfa-research-${state.id}-v${d.version}.html`);
  } else return false;
  return true;
}
async function submitEvolution(form) {
  const data = Object.fromEntries(new FormData(form)),
    buttons = [...form.querySelectorAll("button")];
  buttons.forEach((b) => (b.disabled = true));
  try {
    if (form.dataset.form === "knowledge") {
      data.applies_to = new FormData(form).getAll("applies_to");
      if (!data.entry_id) delete data.entry_id;
      await api("/api/knowledge", data);
      state.knowledgeEdit = null;
      await refresh();
      toast("新知识版本已保存；已采用版本与草案分开保留。");
    } else if (form.dataset.form === "report-snapshot") {
      await api("/api/reports/" + state.id + "/snapshot", {
        reason: data.reason,
        actor: data.actor,
        dependency_digest: state.report.dependency_digest,
      });
      state.showReportSnapshot = false;
      await loadCompany(state.id);
      toast("研究草案快照已保存，估值门槛和旧版仍保留。");
    } else if (form.dataset.form === "information-link") {
      const item = state.information.items.find(
          (i) => i.id === data.information_id,
        ),
        v = await api("/api/companies/" + data.issuer);
      await api("/api/companies/" + data.issuer + "/event", {
        title: item.title,
        published_at: item.published_at.slice(0, 10),
        source_url: item.url,
        mechanism: data.mechanism,
        unknown: data.unknown,
        next_validation: data.next_validation,
        expected_revision: v.revision,
      });
      state.informationLink = null;
      state.information = await api("/api/information");
      renderMarkets();
      toast("已登记待核查事件，公司原结论需要复核；未自动生成财务事实。");
    }
  } catch (e) {
    toast(e.message, true);
  } finally {
    buttons.forEach((b) => (b.disabled = false));
  }
}
