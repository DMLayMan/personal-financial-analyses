# 本地运行、交付与恢复

本项目当前为个人本机服务。用户已要求恢复可访问性，本地后台进程应在本轮工作结束后继续运行；临时验收进程与用户服务分开管理。不会安装系统登录项、开放局域网或远程端口。

```sh
./scripts/start.sh
.venv/bin/python -m pfa.service status
.venv/bin/python -m pfa.service doctor
.venv/bin/python -m pfa.service restart
.venv/bin/python -m pfa.service stop
```

`start.sh`启动后台服务并等待就绪，重复启动返回同一实例。需要前台调试时用 `.venv/bin/python -m pfa.server`。后台实例、日志和锁在 `data/runtime/`，不进入Git。电脑重启或手动停止后重新运行启动命令。尚未安装开机自动启动或崩溃自动拉起。

`/api/healthz`检查数据库可读及worker存活；doctor同时检查首页、JS、bootstrap及代表公司接口。健康成功不等于数据新鲜或研究结论正确，也不是持续可用性SLO证明。服务管理只停止健康端点PID和实例标记均匹配的本项目进程；端口占用或身份不符时保留其他进程并报错。

## 每次交付

1. 备份现有数据库和原件，保存与源码版本的对应关系。
2. 在隔离库运行控制反例、公式、六家流程和必要真实取数；不能把“文件哈希通过”当作整链通过。
3. 重启用户后台服务加载新代码。旧模型因内核摘要变化而需要重算审查，禁止静默重写。
4. 执行status与doctor，并在浏览器检查代表页面及本轮改变的交互。
5. 在另一条独立命令中再次执行status，确认进程不依赖启动会话。保留日志及质量报告，再交付地址。

## 失败处理

- 无法访问：先看status；若stopped则start，unavailable则查看 `data/runtime/server.log`，不要根据失效PID随意杀进程。
- 端口占用：不强制关闭其他服务。核实归属后决定停止本项目或选择新端口。
- 新版错误：在新工作副本检出上一提交，使用兼容数据备份恢复后运行doctor与代表流程；不要覆盖当前库。当前未建立无损跨版本数据库迁移/回滚，数据格式变化前必须补充相应验收。
- 数据源失败：任务保留错误与次数；失败不显示为没有风险。最多三次尝试后转人工处理。
- 备份恢复：按本地指南恢复到新目录，校验文件及数据库；仅数据库恢复而原件缺失不能算完整恢复。

部署参考来自[Google SRE](../quality/references.md)的内部健康与用户路径检查、可重现发布和回退思路。当前单机服务未宣称实现完整生产发布体系；[Python HTTP文档](https://docs.python.org/3/library/http.server.html)也不把标准库服务器推荐为互联网生产服务。
