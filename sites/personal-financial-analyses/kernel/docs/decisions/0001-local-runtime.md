# ADR 0001：本地首版运行与存储

日期：2026年10月25日。状态：本地首版采用；远程版本重新评估。

用户授权按默认方向启动本地开发、优先公开数据，付费数据和远程部署后定。现有设备有 Python，未安装 PostgreSQL 或容器运行环境。

首版采用 Python 标准库 HTTP 服务、SQLite 事务记录与持久任务、原生 HTML/CSS/JavaScript。PDF 读取使用固定版本 pypdf。无需外部模型、账号、数据库服务或构建系统，默认仅绑定 `127.0.0.1`。

财务数字以十进制字符串进入不可变记录，计算使用 Decimal。模型、审查、结论及核验修改采用追加版本。一次命令在一个事务内完成，修改需携带预期研究修订号；事务冲突返回409。来源原件在忽略目录中以校验值追踪，不能把运行数据库纳入Git。

这是对原方案 PostgreSQL 建议默认的本地调整。模块仍按存储、来源任务、证据与研究、确定性模型、监测、HTTP和界面划分。记录层使用JSON保存领域合同，便于迭代，但约束依赖应用校验；尚不是完整关系数据库表设计。多人并发、复杂全文检索和独立远程服务阶段需补充迁移、授权、关系约束及数据库评估。

本地服务的Host、请求令牌、Origin与来源域名检查用于限制本机应用访问，不代表已经完成可公开部署的身份系统。原文内容不执行，也没有进入任何系统提示。未实现外部AI调用；判断由规则约束和个人分步复核完成。

参考：[SQLite官方Python接口](https://docs.python.org/3/library/sqlite3.html)、[Decimal](https://docs.python.org/3/library/decimal.html)、[PDF文字提取的限制](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)。
