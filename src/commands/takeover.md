---
description: 接手项目——把交接文档、密钥位置、开发规范、任务状态一次性加载进上下文并验证接管成功
---

先整篇读 skill 目录 guides/acceptance.md,按其验收纪律执行。对当前工作空间执行接手流程(新 agent 首次进入本项目时手动执行一次;之后仅在自己需要时重新执行):

1. **定位 brain**:当前目录的 `.brain/`;若是 `.brain-home` 指针,去归属仓库(必要时 clone)。
2. **完整阅读**(这是少数应当完整加载而非摘要的场景):HANDOFF.md 全文 → 按其"阅读顺序"读列出的文件 → TASKS.md → `.brain/wiki/index.md`(只读索引,词条按需)→ LESSONS/CONVENTIONS(若存在)。
3. **凭据确认**:按 HANDOFF"资产与访问"的指引确认密钥文件存在、权限正确(600/700);**绝不输出任何密钥值**。缺失时:若项目配置了密钥保险库(HANDOFF 或 `secrets/VAULT.md` 有 vault URL),向用户要一次解锁口令,用 `~/.project-brains/vault.sh pull <secrets-dir> <vault-url>` 恢复;否则按文档指引说明缺什么、从哪拿。
4. **验证接管**:有 `.brain/HANDOFF_ACCEPTANCE.md` 契约 → 按契约逐项执行,每项只允许 PASS/FAIL/BLOCKED/NOT_RUN(FAIL 附失败命令与脱敏错误;BLOCKED 附"需要谁做什么"),报告写入 `.brain/handoff-reports/<UTC>-takeover.md`;无契约 → 真实执行 HANDOFF"如何验证已接管成功"的每条命令并记录,同时提议补建契约文件。
5. **漂移处理**:文档与现实不符的地方,以现实为准修正文档(遵守"记方法不记快照"),commit;push 前先征得用户同意。
6. **接手汇报**:项目目标一句话;已验证的访问能力;活跃任务清单;发现并修正的漂移;逐项验收结果。**只有全部必选项 PASS 且验收报告已提交,才允许声明"接管成功"**;否则结论只能是"部分接管",附阻塞清单与解除条件,"已了解"不是验收。

执行完本命令,本会话即视为"已接手";这些信息不会在后续会话自动重载,新会话需要时重新执行本命令。
