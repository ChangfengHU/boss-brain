# project-brains

给多 agent 工具(Claude Code / Codex / OpenCode / pi-agent)的项目连续性插件:一次安装,所有项目自动获得——行为宪法常驻注入、会话工作空间绑定、按需生长的项目 brain(HANDOFF/任务/证据/llm-wiki)。

设计哲学:**机制学 Trellis(注入、按需加载),体验反 Trellis(零新增概念,只在开工/收工两个边界现身,过程隐身;结构按需生长,不预铺)。**

## 组件(三层)

| 组件 | 载体 | 作用 |
|---|---|---|
| ① 行为宪法 | 各工具全局配置文件(managed block) | 每次对话无条件生效:思维纪律、代码纪律、brain 协议钩子 |
| ② SessionStart hook | Claude Code `settings.json` | 开场强制:未绑定工作空间 → 提示选项目;有 brain → 自动加载 |
| ③ project-brains skill | 各工具 skills 目录 | 懒加载协议手册:绑定、初始化、HANDOFF 定位、证据格式、wiki schema |

## 安装 / 验证 / 升级

```bash
# 任何机器一键安装(公网,SHA256 校验,零凭据):
bash <(curl -fsSL "https://skill.vyibc.com/install-project-brains.sh")

# 或从仓库本地安装:
bash install.sh   # 幂等;探测到哪个工具装哪个,打印各工具能力档位
bash doctor.sh    # 逐项 PASS/FAIL
```

发布新版本: `bash scripts/release.sh`(需 R2 上传凭据;产物落 R2 + `releases/current/`,git 为持久权威)。

升级 = git pull 后重跑 install.sh(managed block 原地替换,不碰用户自己的内容)。

## 四个命令(Claude Code 输 `/xxx`;Codex 有命名空间前缀,输 `/prompts:xxx`,如 `/prompts:brain-init`——直接输 `/xxx` 会被当普通文字)

- **`/handoff-show` 预览**:只读展示 HANDOFF 现状与完整度评分(X/10)、"接手者会卡在哪",供用户人工判断;不做任何修改。
- **`/handoff` 交接**:确定要交接时手动执行——逐项校验交接文档质量(完整性、快照污染、验证命令实跑、状态一致、无密钥明文),能修的当场修,最后 commit 并**征得用户同意后 push**,给出"交接就绪/未就绪"结论。任何流程中 push 都不是默认动作(公司仓库可能禁推),必须用户本次明确同意。
- **`/takeover` 接手**:新 agent 首次进项目时手动执行一次——把 HANDOFF、密钥位置、规范、任务状态完整加载进上下文,实跑验证命令,修正漂移,汇报接管结果。此包信息**不随会话自动加载**(区别于宪法),之后仅在自己需要时重新执行。

## 核心规则(细节见 skill/project-brains/SKILL.md)

- 会话开始未绑定工作空间(如在 home 根目录)→ 先问开发哪个项目:已登记项目 / 本地目录 / GitHub 仓库(clone 到 `~/projects/`),**不默认当前目录**。
- 初始化只建 `.brain/HANDOFF.md` 一个文件,其余结构按需生长。
- HANDOFF = 接收协议(零上下文者如何接管),只随世界结构变化更新;稳定文档记方法不记快照。
- 有 commit 才落证据(JSONL,含真实验证命令与 exit code);纯问答零写入。
- wiki 入库标准 = 重获成本;蒸馏不转录;先查后干;lint 防腐。
- 多任务:每任务独立记录文件,并发会话零冲突;"继续"有歧义时列清单让用户选。
- `.brain-home` 指针:brain 托管在别处的项目(如 suqu 各业务仓库 → suqu-control-plane),记录写归属地,不重复建脑。

## 能力档位(v0.3.0 实况)

| 工具 | 宪法 | 开场注入 | 收工强制 | 命令 | skill |
|---|---|---|---|---|---|
| Claude Code | ✅ | ✅ SessionStart hook | ✅ Stop hook(有 commit 无证据即拦截) | ✅ 三命令 | ✅ |
| Codex | ✅ | prelude(宪法) | 宪法软约束 | ✅ prompts 三命令 | ✅ |
| pi-agent | ✅ | ✅ TS extension(严格类型检查过;TUI 实跑待验) | 宪法软约束 | skill 流程触发 | ✅ |
| OpenCode | ✅(检测到才装) | 宪法 | 宪法软约束 | skill 流程触发 | ✅ |
| Gemini CLI | ✅ | 宪法 | 宪法软约束 | — | — |

## 密钥保险库(vault)

`scripts/vault.sh push|pull|status`:密文(AES-256-CBC + PBKDF2 60 万次迭代)存 R2,
口令只在用户脑中,pull 自动恢复 700/600 权限。已通过端到端测试:往返一致、错口令拒绝、
密文不含明文、SHA 校验。项目在 HANDOFF 或 `secrets/VAULT.md` 里记 vault URL 即接入。

## 行为探针(probes/)

`bash probes/run.sh [重复次数]`:每条不可硬强制的宪法条款一个无头探针
(先陈述假设 / 直接指出漏洞不奉承 / 未绑定工作空间先问项目),中立目录运行,按输出判分。

## 路线图(剩余)

1. OpenCode JS 插件(本机未装该工具,无法验证,暂不发未测代码)。
2. pi extension 的 TUI 实跑验收(需要真实 pi 会话,用户侧一次即可)。
3. 真实秘钥入库(vault 已就绪,等用户定一次口令执行 push)。
