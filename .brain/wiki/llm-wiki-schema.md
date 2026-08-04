# llm-wiki-schema — Karpathy 三层的适配

## 问题
项目知识(苦战结论、深度问答)不能"这次过去了就再也没有了";怎么设计项目级 llm-wiki?

## 结论
采用 Karpathy llm-wiki(gist 442a6bf, 2026-04)三层:raw(不可变源)/ wiki(LLM 拥有的编译层)/ schema(维护规则),加 ingest/query/lint 三操作、[[links]]、index.md、log.md。

三处适配:
1. **raw 层=证据流**:我们的原始源不是人放的文章,是开发自动产出的 evidence/dev-log——raw 层自动生长,人零搬运;
2. **schema 拆两截**:一行触发钩子进宪法(常驻、便宜:"遇难题先查 index;高重获成本要提议入库"),完整 schema 进 skill(懒加载)——Karpathy 把 schema 放项目 CLAUDE.md 会肥常驻层;
3. **ingest 由重获成本驱动**(苦战后/用户说记下来/agent 自判),不是"往 raw/ 放文件"驱动。

刻意不照搬:不预分 entities/concepts/syntheses 目录,平铺至 ~30 词条再分类;工艺=蒸馏不转录;query 好答案反哺成词条;lint 清单(矛盾/被推翻声明/孤儿页/缺页)低频跑。

## 关联
[[trigger-granularity]] [[design-philosophy]]

2026-08-04。过期风险:中(Karpathy 模式若有新版需对照)。
