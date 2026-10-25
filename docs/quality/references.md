# 审查与运行参考依据

查阅日期：2026年10月25日。以下均为公开一手材料；这里借鉴方法，不声称本项目获得认证或取得机构内部流程。

| 编号 | 原始材料 | 本项目采用的检查 | 适用边界 |
| --- | --- | --- | --- |
| Q1 | [CFA V(A) Diligence and Reasonable Basis](https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-v-a) | 检查依据、第三方研究、时效、假设和可测量研究质量；每条重要意见追到适用证据 | 研究依据充分不保证收益；借鉴职业研究纪律，不宣称认证 |
| Q2 | [Fed SR26-2正文](https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm)及[2026附件](https://www.federalreserve.gov/supervisionreg/srletters/SR2602a1.pdf) | 分别评价概念合理性、结果比较、持续监测、有效质疑及用途限制 | 2026年4月17日已替代SR11-7与SR21-8；主要面向银行。生成式/代理式AI不在附件范围内，不能将其当本平台的强制要求或AI有效性证明 |
| Q3 | [Damodaran：PE的基本决定因素](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/lectures/pe.html) | 终值PE与增长、分配及风险的关系；拒绝把倍数当孤立旋钮 | 历史课堂案例不是当前股票目标价；参数仍需公司证据 |
| Q4 | [Damodaran：增长的基本决定因素](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/invfables/growthdeterminants.htm) | 增长、留存与资本回报的一致性；检查增长是否需要额外投入 | 实际公司存在业务结构、杠杆和资本变化，不能机械套稳态关系 |
| Q5 | [CFA：股利折现估值](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation) | 方法选择、分配、增长、折现与终值假设；银行RI另以同假设DDM核对 | 同假设两方法相等仅验证代数，不证明ROE、资本分配和当前价值 |
| Q6 | [Google SRE：监测分布式系统](https://sre.google/sre-book/monitoring-distributed-systems/) | 同时检查内部健康和用户实际页面；区分可用性、错误与返回错误内容 | 当前本地doctor和浏览器是点时检查，尚无持续SLO样本 |
| Q7 | [Google SRE：发布与渐进验证](https://sre.google/workbook/canarying-releases/) | 保存构建输入、自动检查、小步变更和回退依据 | 本地单用户没有假装做多用户canary；远程发布流程待部署阶段 |
| Q8 | [Python HTTP服务文档](https://docs.python.org/3/library/http.server.html) | 明确当前HTTP服务的本地用途，远程服务需重新设计身份和运行方式 | 标准库服务不被当作互联网生产服务器 |
| Q9 | [SEC EDGAR数据接口](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | 发行人、表单、上下文、期间和原文核对；不以latest filed取代正确期间 | 标准化标签不覆盖全部经营KPI，不代表历史当时快照 |

这些来源支持检查方向。项目的功能编号、失败门槛、测试题和阶段安排是本项目的设计，具体执行证据见[自查](review-2026-10-25.md)和[验证标准](verification-standard.md)。

## 0.4三层平台新增依据

- Q10：[Bloomberg产品](https://professional.bloomberg.com/products/)。借鉴数据、经济、图表、研究、分析与工作流的组合，不声称复制或获得其数据。
- Q11：[FRED数据](https://fred.stlouisfed.org/series/DGS10)。按系列保留定义、单位、日期、提供者与修订，公开可读不代表实时或不限分发。
- Q12：[MSCI GICS](https://www.msci.com/indexes/index-resources/gics)。借鉴行业层级；项目六类为自定义经济机制，未做正式授权映射。
- Q13：[FRED 2年国债](https://fred.stlouisfed.org/series/DGS2)、[Brent现货](https://fred.stlouisfed.org/series/DCOILBRENTEU)。bp、同日曲线及现货/期货定义分开。
- Q14：[美联储SVB审查](https://www.federalreserve.gov/publications/review-of-the-federal-reserves-supervision-and-regulation-of-silicon-valley-bank.htm)。风险经验需考察期限/利率/集中融资和流动性联动，事后解释不当作事前预测。
