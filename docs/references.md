# Personal Financial Analyses 参考来源

版本 0.1
核查日期 2026年10月25日

这些材料支持研究思想和方法。项目中的状态、补证条件、数据合同、可信度表达和功能划分是本项目的设计，不代表原作者制定的软件规程，也不推测作者对当前公司的实际判断。

## 研究思想与方法

| 标识 | 原始材料 | 在本项目中的用途 |
| --- | --- | --- |
| S1 | [Warren Buffett 1996股东信](https://www.berkshirehathaway.com/letters/1996.html) | 能力圈、业务理解与买入价格 |
| S2 | [Warren Buffett 1986股东信及附录](https://www.berkshirehathaway.com/letters/1986.html) | 所有者收益、维持投入及估计的不确定性 |
| S3 | [Charles Munger 授权演讲集](https://www.stripe.press/poor-charlies-almanack/book) | 多模型、激励、机会成本及判断偏差 |
| S4 | [Munger Practical Thought about Practical Thought](https://www.stripe.press/poor-charlies-almanack/talk-four) | 反向思考；授权演讲集亦包含对应内容 |
| S5 | [CFA Research Foundation 1977文献内1976年Graham访谈](https://rpc.cfainstitute.org/sites/default/files/-/media/documents/book/rf-publication/1977/rf-v1977-n1-4731-pdf.pdf) | 晚期低估组合法、分散和策略背景；印刷第33至41页 |
| S6 | [Fidelity Peter Lynch访谈 2022年11月3日](https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/learning-center/110322%20rewards%20exclusive_UnderstandtheChange-Transcript_%20F.pdf) | 理解业务、产品线索后的调查、扩张与生存能力 |
| S7 | [Howard Marks Risk Revisited Again 2015年6月8日](https://www.oaktreecapital.com/docs/default-source/memos/2015-06-08-risk-revisited-again.pdf) | 永久损失、被迫出售、波动及模型边界 |
| S8 | [Howard Marks I Beg to Differ 2022年7月26日](https://www.oaktreecapital.com/insights/memo/i-beg-to-differ) | 价格、共识和差异化判断 |
| S9 | [CFA Diligence and Reasonable Basis](https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-v-a) | 研究依据和第三方资料核查 |
| S10 | [Gneiting与Raftery 2007 概率评分研究](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf) | 适当评分规则及预测评价 |
| S11 | [Ronald Howard 1966 Information Value Theory](https://ieeexplore.ieee.org/document/4082064/) | 信息对决定的价值；项目采用定性补证优先级 |
| S12 | [Carpenter与Lynch 1998工作论文](https://archive.nyu.edu/jspui/bitstream/2451/27075/2/wpa98077.pdf) | 幸存者、前视和样本选择偏差；后发表于1999年JFE |
| S13 | [IPCC 2010 不确定性处理指南](https://www.ipcc.ch/site/assets/uploads/2018/12/ar5_uncertainty-guidance-note.pdf) | 借鉴证据信心与事件可能性的区分，不移植其数字等级 |
| S14 | [SEC EDGAR API说明](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | 公开申报记录和部分XBRL接口 |
| S15 | [FactSet历史时点一致预期方法](https://insight.factset.com/hubfs/Resources%20Section/White%20Papers/ID11996_point_in_time.pdf) | 历史信息集、预期快照与时间口径 |
| S16 | [NIST AI RMF 1.0](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) | 区分有效性、解释性、可靠性与持续评价 |

公开页面或章节入口可能随时变化。来源核查记录不代表取得其全文批量留存或应用展示许可。当前资料中的思想归纳应与作者原文一并阅读。

## 技术参考

- [PostgreSQL精确数值类型](https://www.postgresql.org/docs/current/datatype-numeric.html)：支持金额等需要精确表示的字段。精度、舍入与应用计算仍需要设计与测试。
- [PostgreSQL事务隔离](https://www.postgresql.org/docs/current/transaction-iso.html)：用于考虑并发读取和一致发布；不代表系统已经实现相应事务策略。
- [PostgreSQL行级策略](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)：多用户隔离的候选工具，不能单独替代完整授权设计。

上述技术文档用于核查方案建议，没有据此固定生产版本或完成部署。

## 样本来源

六家公司原始资料和本次实际读取状态单独保存在[数据源清单](data-sources.md)与[样本验证摘要](validation/pilot-findings.md)，避免将一般方法文献当成公司事实的证据。
