# multi-task-binding — 会话绑定任务,brain 是停车场

## 问题
用户习惯在同一目录(甚至 home 根目录)开 N 个会话各干各的。全局 current-task 指针 + 单一全局 handoff 的单线程假设在此崩溃(suqu 的 .suqu/current-task 即此毛病)。

## 结论
- 项目级共享(规范/教训/密钥索引)与任务级隔离(进度/证据)分开;每任务独立 evidence 文件,并发会话零写冲突。
- 绑定是**会话内状态**,不写全局:开场绑定一个任务;"继续"有歧义(多活跃任务)时列清单让用户选,自动挑是 bug;"继续做X"按描述匹配。
- home 根目录不是项目:SessionStart hook 提示选工作空间(已登记/本地目录/GitHub clone),绝不默认 cwd。
- 一个仓库只认一个 brain 归属:.brain-home 指针指向归属仓库(如 suqu 业务仓库 → suqu-control-plane),不重复建脑。

## 关联
[[design-philosophy]] [[handoff-positioning]]

2026-08-04。过期风险:低。
