# Personal Financial Analyses

Personal Financial Analyses 是面向个人深度研究与中长期投资的商业与金融分析终端，覆盖美股、港股和 A 股。项目以研究问题、原始证据、经营机制、盈利与估值、风险和持续复核为主线。

当前0.5按平台基础、市场信息、行业公司三层组织，可用于本地来源台账、历史算术、示例敏感性与人工研究记录。自查发现0.2在补证、期间、证据分类、验收和交付上存在实质缺陷，已补反例及控制。个股经营驱动、盈利承保、当前公允价值和投资效果仍未通过研究质量验收，见[自查报告](docs/quality/review-2026-10-25.md)。

直接运行 `./scripts/start.sh` 启动独立后台服务，打开 `http://127.0.0.1:8765`。查看状态用 `.venv/bin/python -m pfa.service status`。用户服务在交付后继续运行，电脑重启后需重新启动；详见[本地运行手册](docs/operations/local-service.md)。

0.5新增知识增修/停用与采用版本、Fed/选定SEC元数据、证据判断链、报告快照/依赖和可独立阅读的HTML。三个主方向在各断点均位于左侧。市场和信息仍按需读取，尚未接连续实时推送。

网站首先展示平台方法、Agent职责合同、知识和审查；第二层是跨市场大盘、来源状态和行业传导；第三层按六种经济机制阅读公司研究报告。公开延迟快照、人工转录和待接入目录分开，不宣称自主Agent已运行或当前证券估值已获验证。

## 项目信息

| 项目 | 约定 |
| --- | --- |
| 英文名称 | Personal Financial Analyses |
| 中文工作名 | 个人金融分析终端 |
| 仓库标识 | personal-financial-analyses |
| 当前版本 | 0.6.0 |
| 基线日期 | 2026年10月25日 |
| 当前阶段 | 三层平台、公开市场快照、行业手册及报告；继续深化经营驱动和研究验证 |

英文名称保留用户指定的 `Analyses`。中文工作名对本次口述中的“个人分金融分析终端”作去除重复字的整理；不影响英文项目标识。

## 文档入口

| 文档 | 内容与使用方式 |
| --- | --- |
| [报告内核与长期迭代](docs/report-product-design.md) | 知识版本、真实信息接入、判断链、报告快照及扩展门槛 |
| [机构报告对照](docs/institutional-report-benchmark.md) | 实际读取的DBS/Goldman Sachs/UBS公开样本与采用边界 |
| [0.5验收](docs/validation/local-v0.5.md) | 左侧导航、知识增修、公开信息和可读报告的实际验证 |
| [三层平台方案](docs/three-layer-architecture.md) | 平台基础→市场与信息→行业/公司报告的结构、依赖、边界和扩展 |
| [市场框架](docs/market-framework.md) | 大盘指标、来源、时间/单位、缺失与传导规则 |
| [行业与报告](docs/industry-research.md) | 六类行业经济机制、研究职责与报告合同 |
| [0.4验收](docs/validation/local-v0.4.md) | 三层功能、数据可得性及浏览器验证 |
| [用户需求](docs/requirements.md) | 用户目标、原始要求、确认程度、范围和验收条件，是需求依据 |
| [当前质量判定](docs/quality/review-2026-10-25.md) | 实际反例、整改、六家公司研究差距与允许用途 |
| [每项功能与验收](docs/quality/feature-plan.md) | 19项功能、知识/信息/报告版本及六公司驱动桥、事前门槛及实施顺序 |
| [验证标准](docs/quality/verification-standard.md) | 软件、原文、语义、金融方法、保留集、前瞻及运行分别评估 |
| [审查参考](docs/quality/references.md) | CFA、2026模型风险指导、NYU估值与SRE原始材料 |
| [最新功能检查](quality/latest-functional.json) | 实际运行、源码摘要和逐项结果；单独保留研究未验证状态 |
| [0.3交付验收](docs/validation/local-v0.3.md) | 反例整改、当前功能检查与交付后的访问验证 |
| [本地运行指南](docs/local-development.md) | 启动、研究操作、模型边界、测试、导出与备份恢复 |
| [首版验收](docs/validation/local-v0.2.md) | 六家实际流程、原文与异常验收边界 |
| [本地运行决定](docs/decisions/0001-local-runtime.md) | Python、SQLite及与原设计建议的关系 |
| [方案与技术设计](docs/solution-design.md) | 当前解决方案、系统边界、数据对象、研究流程和技术实现约束 |
| [研究与决策规程](docs/research-methodology.md) | 此前 V1 规程的文本基线，规定如何研究、补证、判断和复核 |
| [数据源与验证状态](docs/data-sources.md) | 区分规划、已读取、已核验、可持续更新和使用权限 |
| [样本验证记录](docs/validation/pilot-findings.md) | 六家样本带来的设计发现及验证边界 |
| [开工条件与待定输入](docs/readiness.md) | 哪些已经明确，哪些可以按默认推进，哪些在特定阶段需要输入 |
| [参考来源](docs/references.md) | 研究思想、校准方法和技术选择的公开来源 |
| [变更记录](CHANGELOG.md) | 基线与后续变更摘要 |

## 文档治理

需求、设计、研究规程和验证证据分别维护。需求变化应更新对应需求编号、设计映射和验收条件；设计建议不能自动升级为用户已确认的要求。技术选型、数据采购和部署决定应记录理由及适用范围。

原有 [Word 研究规程](research-design-2026-10-25/personal-business-research-framework-v1.docx) 保留为历史快照。后续正式文本以 `docs/` 内的 Git 版本为准，不要求 Word 快照与每次文本变更同步。

## Git 管理

沿用当前工作目录的 Git 仓库。文档、应用与测试代码、已标记来源的公开选定字段进入版本控制；运行数据库、下载原件、缓存和凭据保留在 Git 之外。0.1保留文档基线，0.2新增本地实现。

项目远端为 [DMLayMan/personal-financial-analyses](https://github.com/DMLayMan/personal-financial-analyses)（私有仓库），默认分支为 `main`。完整提交历史已上传，本地开发分支跟踪 `origin/main`。

后续开发须按[AGENTS.md](AGENTS.md)登记功能合同并留存验证结果。可运行 `.venv/bin/python scripts/quality_gate.py --live` 更新本地功能检查；该检查不会把测试通过升级为投资判断可靠。

## 私有远程版 0.6

[打开 Personal Financial Analyses](https://personal-financial-analyses-wktt.august247wk.chatgpt.site)。仅本人使用 ChatGPT 登录，可在其他设备访问。站点托管源码在 `sites/personal-financial-analyses/`，身份保存在该目录的 `.openai/hosting.json`。

云端保存研究数据库、原件和版本；浏览器复用同一Python研究内核。仅按需更新，关闭页面后不持续监测。本地与云端在首次迁移后分别版本化，没有自动双向同步。首次证据包约59MB，另需加载Python运行时。

本轮修复事实/文件日期混用、未读披露遗漏、非正同比基数丢失、普通股利润标题和内核变更漏审；未将工程通过升级为行业预测或投资效果通过。见[深度审查](docs/quality/review-2026-10-25.md)、[远程运行](docs/operations/hosted-service.md)与[功能合同](docs/quality/feature-plan.md)。正式站点已部署并迁移；自动化浏览器被OpenAI登录安全验证阻挡，完整登录后的线上浏览器验收仍待本人常用浏览器确认。
