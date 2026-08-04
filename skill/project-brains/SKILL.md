---
name: project-brains
description: Project continuity protocol. Use when a session starts without a bound workspace (e.g. opened in home dir), when the user says 继续/换项目/初始化项目/接手项目, when work produces commits that need evidence records, when the user or agent wants to save hard-won knowledge (记下来/沉淀/记教训/wiki), or when HANDOFF/TASKS/.brain files need to be created or updated.
---

# project-brains 协议

你是这套协议的执行者。原则:系统只在边界(开工/收工)现身,过程零打扰;结构按需生长,不预铺;无状态变化零写入。

## 1. 会话工作空间绑定(每个会话的第一件事)

会话未绑定工作空间时(SessionStart hook 会注入提示,典型情况:在 home 根目录打开):

1. 问用户本次开发哪个项目。给出三类选择:
   - 已登记项目(读 `~/.project-brains/registry.tsv`,格式 `路径<TAB>名称`,逐行列出);
   - 一个本地目录路径;
   - 一个 GitHub 仓库(clone 到 `~/projects/<repo名>`,已存在则 `git pull` 后复用)。
2. **绝不默认使用当前目录当工作空间**;用户明说"就在这个目录"除外。
3. 绑定后 cd 到该目录工作;绑定关系只属于本会话,不写全局状态。
4. 目录若有 `.brain-home` 文件(内容是另一仓库路径/名称),说明该项目的 brain 托管在别处(如控制平面仓库),记录一律写到那边,本地不建 `.brain/`。

## 2. brain 初始化(新项目,经用户同意)

只做两件事:

1. 创建 `.brain/HANDOFF.md`(用第 3 节的模板,能填的填,不能填的留 TODO);
2. 向 `~/.project-brains/registry.tsv` 追加一行 `绝对路径<TAB>项目名`(已存在则跳过)。

不预建任何其他文件或目录。TASKS.md 在第一个任务出现时创建;`tasks/<id>/` 在第二个并发任务出现时才分裂;LESSONS.md 在第一次踩坑时创建;`wiki/` 在第一个词条入库时创建。

## 3. HANDOFF.md:接收协议(不是进度报告)

定位:**假设读者零上下文**,回答"如何从一无所有到完全接管"。它不是 dev-log、不是任务清单、不是 README、不是技术文档。

模板:

```markdown
# HANDOFF — <项目名>

## 这是什么
<一两句话;详细看 README>

## 资产与访问
<机器/服务/仓库在哪;权限和密钥怎么拿到(指向位置,绝不写值)>

## 接手阅读顺序
<依次读哪几个文件>

## 如何验证已接管成功
<几条永远有效的验证命令/方法>

## 雷区
<不可逆操作禁令、已知陷阱>
```

更新触发器:**只有世界结构变化**——新机器、新密钥位置、新服务、新约定、验证方法变化、引入新子项目。完成任务、进度推进一律不动它。收工时自问一句"这次改动动没动世界结构",动了才提议更新。

硬规则:**稳定文档记方法不记快照**。写"用 `git log -1` 查当前部署",不写"当前部署是 abc123"。commit 号、版本号等易变数字只允许出现在证据记录里。

## 4. 任务与多任务

- `.brain/TASKS.md`:活跃任务清单,一行一任务:`t-<序号> <简述> <状态: active/blocked/done>`。
- 单任务项目:证据直接写 `.brain/evidence.jsonl`,不建目录。
- 出现第二个并发任务时:分裂为 `.brain/tasks/<t-id>/evidence.jsonl`,各任务各写各的文件,并发会话零冲突。
- 用户只说"继续"且有多个 active 任务:**列出清单让用户选,不自动挑**。说"继续做X"则按描述匹配绑定。
- 会话内容是新事情:新建任务条目,不碰其他任务。

## 5. 证据记录(收工时,仅当本会话产生了 commit)

向对应 evidence.jsonl 追加一行 JSON:

```json
{"date":"2026-08-04","task":"t-1","summary":"一句话","files":["a.js"],"verify":"node test.js","exit":0,"risks":"残余风险或 none","commit":"<hash>"}
```

- `verify` 必须是真实运行过的命令,`exit` 是真实退出码;没验证就写 `"verify":"none"`,不许编。
- dev-log 不单独写——evidence 就是日志源,需要人读的摘要从它生成。
- 纯问答会话:什么都不写,不解释,不提议。

## 6. wiki(项目的 llm-wiki)

**入库标准:重获成本**——重新获得这份认知要花多少钱。苦战几小时的排查结论、追问多轮得出的深度解答、查了很多资料才想通的机制 → 入库;随手能再查到的 → 不入。

三个触发:① 苦战之后 agent 主动提议;② 用户说"记下来/这个回答很好"(必须执行);③ 回答完有持久价值的深度问题时提议。

结构(平铺,词条超过 ~30 个再谈分类):

```
.brain/wiki/
  index.md      ← 每词条一行:标题 + 一句钩子。查询先扫这里
  log.md        ← append-only:## [日期] ingest|query|lint | 标题
  <slug>.md     ← 词条
```

词条格式:标题 / 问题是什么 / 结论 / 证据与推理 / 关联 `[[其他词条]]` / 日期与可能过期点。

工艺:**蒸馏不转录**——重写成不依赖对话上下文、单独可读的文章;禁止粘贴聊天记录。"记方法不记快照"同样适用。

读取纪律:遇难题先扫 `index.md`;query 合成出的好答案问一句"要不要成为新词条"。

lint(低频,用户说"lint wiki"或冷启动演练时顺带):找词条间矛盾、被新认知推翻的旧声明、零入链孤儿词条、该有专页却没有的概念。

毕业通道:词条被反复引用 → 蒸馏成一条规范进 CONVENTIONS/宪法,或升级成 skill/脚本。

## 7. 三个显式命令(用户的三个郑重时刻)

- `/brain-init`(接入):存量项目首次接入——从现有资料(README/文档/git 历史)蒸馏出 HANDOFF,不铺空模板;确认不了的写 TODO 并当场问用户。
- `/handoff`(交接):用户确定要交接时执行——按命令文件逐项校验交接质量并做最后优化,commit+push,给出"交接就绪/未就绪"结论。
- `/takeover`(接手):新 agent 首次进项目执行一次——完整加载 HANDOFF/密钥位置/规范/任务状态进上下文,实跑验证,修漂移,汇报。不随会话自动重载;后续自己需要时可再执行。
- 无命令体系的工具里,用户说"初始化一下/交接一下/接手一下"等价触发,按本 skill 同名流程执行。

## 7.5 密钥保险库(vault)

密文存 R2,口令只在用户脑中。工具:`~/.project-brains/vault.sh`(或仓库 `scripts/vault.sh`)。

- **恢复**(新机器/密钥缺失):项目 HANDOFF 或 `secrets/VAULT.md` 里有 vault URL →
  向用户要一次解锁口令 → `vault.sh pull <secrets-dir> <vault-url>`(自动 700/600)。
- **同步**(密钥变更后):`vault.sh push <secrets-dir> <vault-url>`(需 R2 上传凭据)。
- 口令绝不写入任何文件/文档/日志;`VAULT_PASSPHRASE` 环境变量仅限脚本内部传递,用后即弃。
- 解密失败=口令错或密文损坏,报错后重新向用户确认口令,不要瞎试。

## 8. 收工检查清单(Stop 前自查,30 秒)

1. 本会话有 commit?→ 落证据记录;没有 → 什么都不写。
2. 动了世界结构?→ 提议更新 HANDOFF;没动 → 不碰。
3. 有高重获成本认知?→ 提议入 wiki。
4. 任务状态变了?→ 更新 TASKS.md 那一行。
5. 全程未输出任何密钥明文。
