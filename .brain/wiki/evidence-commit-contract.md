# 证据 commit 指针契约:禁 amend,不留 pending

## 问题是什么
外部对抗审计发现 evidence.jsonl 14 条记录里 10 条的 commit 指针失效:
6 条写着 `"pending"` 从未回填,4 条指向被 `--amend` 改写后的孤儿 hash
(`git branch --contains` 为空)。工作全部真实,但"证据→diff"的跳转链断了。

## 结论
两条铁律:
1. **禁止 amend 并入**:证据行不得用 `git commit --amend` 塞进它所记录的工作 commit——
   amend 改写 hash,证据里的指针写下即作废。正确顺序:工作 commit →
   `git rev-parse --short HEAD` 取 hash 写进证据 → 证据/dev-log 单独 `docs(brain)` commit。
2. **禁止 "pending" 占位**:回填承诺必然被遗忘(6/6 全没回填)。当场取不到 hash
   就说明顺序错了,先 commit 再写证据。

鸡生蛋问题的正解:证据自身的 commit 不需要被自己记录——它是下一条证据的工作背景,
或根本不值一条记录(纯记账)。

## 证据与推理
2026-08-06 独立 subagent 审计报告;修复 commit 见本仓库 git log(证据指针全量修复)。
审计还发现讽刺样本:自称修复"证据 commit 竞态"的那条记录,自己记的就是孤儿 hash——
说明该 bug 靠自觉不可修,必须变成写入纪律(本词条)+ 机读检查(未来 lint 可校验
`git merge-base --is-ancestor`)。

## 关联
[[soft-vs-hard-discipline]] · [[trigger-granularity]]

## 日期与可能过期点
2026-08-06。若未来 evidence 写入完全脚本化(不经模型手写),本契约可降级为脚本内部实现细节。
