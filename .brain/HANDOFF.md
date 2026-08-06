# HANDOFF — project-brains

## 这是什么
多 agent 工具的项目连续性插件(宪法+hook+skill 三件套)。详细看 README.md。

## 资产与访问
- 本仓库是唯一权威;GitHub: ChangfengHU/project-brains(凭据在 suqu-control-plane `secrets/private/`,取用方法见该仓库 HANDOFF)。
- 安装产物落在各工具目录与 `~/.project-brains/`,全部可由 install.sh 重建,无独有状态。

## 接手阅读顺序
1. README.md(是什么、组件、档位、/handoff 与 /takeover 命令)
2. skill/project-brains/SKILL.md(协议全文)
3. constitution/global-directives.md(宪法单一源)
4. .brain/wiki/index.md(设计思想词条,理解"为什么这样设计"必读)
5. install.sh / doctor.sh(怎么铺、怎么验)

## 如何验证已接管成功
- `bash doctor.sh` 全 PASS。
- `echo '{"cwd":"'$HOME'"}' | ~/.project-brains/hooks/session-start.sh` 输出工作空间选择提示。
- 改 constitution 后重跑 install.sh,确认目标文件 managed block 被原地替换且用户内容未动。

## 雷区
- install.sh 只能通过 managed block 标记编辑用户的全局配置文件,禁止整文件覆盖。
- 设计原则(反 Trellis:零新概念、按需生长、边界现身)是本项目的灵魂,加功能前先对照 README 设计哲学一节。
- 设计思想已沉淀在 `.brain/wiki/`(篇目见 index.md);改动方案前先读,别重新发明或违背。
