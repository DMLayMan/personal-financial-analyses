# 0.6私有远程版交付与验证

2026-10-25。真实发布状态`succeeded`，地址[Personal Financial Analyses](https://personal-financial-analyses-wktt.august247wk.chatgpt.site)，权限为owner-private；源代码提交`37ed569336a248a532ef7281c1c5810be2a4087d`。站点与数据不依赖本机常开。

## 已完成和实际依据

| 层次 | 本轮结果 | 证据与边界 |
| --- | --- | --- |
| 本地内核与控制 | 90项Python测试、5项托管策略检查通过，运行内核与源码相符 | `quality/latest-functional.json`，不是财务预测有效性认证 |
| 浏览器Python兼容性 | 最终源包39项控制/公式基准通过 | 同版本Pyodide实际浏览器执行；含独立年金计算、银行RI边界、原文口径、非正基数、内核修订等 |
| 三层与六家公司 | 六份报告均有证据、传导、财务影响、反方和下一验证；保留未评级 | 可丢弃本地托管预览的可视检查，不冒称正式登录后验收 |
| 原文读取 | 浏览器pypdf实际定位宁德Q3 PDF第11/13页，显示现金流表 | 页面抽取仍为定位辅助，不自动证明事实或解释正确 |
| 云端保存 | 保存到云端确认后才提示成功；刷新后已存版本/原因仍在 | 本地D1/R2预览，实际并发两提交只有一笔成功，另一笔409 |
| 公开源刷新 | 浏览器通过受控代理请求13个市场源；9个Yahoo序列成功，4个FRED序列25秒超时，保留旧观察日期及失败任务 | 按需获取；实际可得性为9/13；并非全部成功。生产网络可得性尚需登录后复查 |
| 真实线上 | 匿名访问被登录边界保护，已部署核心源码与已审本地代码一致；数据库SHA及三类原件抽样一致 | 97份资料及云端v1持久化；部署替换后数据保留；`v06-private-deployment-checks.json` |
| 线上六份报告复算 | 从真实云端数据库重建六份草案，CATL现金桥/CMB普通股标题正常 | 在本地已审Python执行；没有称为正式浏览器已登录通过 |
| 线上登录 | **未完成端到端验收** | OpenAI登录先出现400后转安全验证。需本人常用浏览器登录；不绕过验证、不改公开访问 |
| 手机 | **本轮未计作通过** | 后台预览视口覆盖未生效，实际仍1280px；未拿桌面结果冒称390px或真实手机验证 |

关键反例原始失败分别在`v06-counterexamples-before.txt`、`v06-bank-label-before.txt`及`v06-report-kernel-before.txt`。浏览器结果见`quality/evidence/v06-browser-checks.json`；本地并发/保护检查见`v06-cloud-local-controls.json`。操作、限制及恢复步骤见[远程运行](../operations/hosted-service.md)。

## 研究用途与下一轮验收

仍适合来源台账、可比历史算术、现金观察、通用示例敏感性和人工审议/留痕。仍未通过有证据承保的行业预测、同一时点现价估值、最强反方语义充分性和前瞻投资效果。下一轮先做BYD融资/资金、CATL营运资本、CMB信用与资本的可复算桥，再扩展MSFT/COST/腾讯；逐项预写原文答案和失败条件。详见[审查结论](../quality/review-2026-10-25.md)与[功能合同](../quality/feature-plan.md)。

公开源本轮原始结果见`quality/evidence/v06-source-refresh-result.json`。失败项为us10y、us2y、hy_oas、brent_spot；不能把已存在的较早FRED快照当成本轮新取得。
