Boss Brain 帮助

Boss Brain 是开发辅助层：Boss 管本机项目和会话，项目 .brain 保存状态、任务、规范与经验。
它帮助 Agent 接续工作，但不会自动证明业务正确，也不会因为提到某个项目就获得修改权限。

对话里可以说：help boss、boss help、boss 帮助。
终端使用：boss help；详细说明：boss help receipt、boss help session mode。
这里的命令都是示例，查看帮助不会执行它们。SESSION 请替换为真实会话 ID。

不知道从哪开始？
  想知道管了哪些项目：boss projects，再用 boss status 看工作区状态。
  想知道识别是否正确：boss explain --session SESSION --show。
  想看到真实执行过程：boss help display，然后 boss help events；不依赖 Agent 口头回执。
  想让某项目每轮提示：boss help receipt；里面说明全局与项目覆盖的区别、效果及恢复方法。
  想临时停用本会话：boss help session mode；它不会清除已加载的全局规则。
  想接管已有仓库：boss help adopt；确认写入范围后再执行，不必先做全局初始化仪式。
  想沉淀经验或交接：boss help knowledge 或 boss help handoff。

下面是导航，不必记住全部命令。任意主题都可用 boss help 命令名 查看用途、场景、
影响范围、参数、示例和预期结果；例如 boss help knowledge resolve。

查看信息（只读）
  boss projects                 项目列表
  boss status                   项目 Git 状态
  boss caps                     能力与项目依赖
  boss risk                     风险与阻塞
  boss explain --session SESSION --show   本会话加载了什么
  boss doctor                   基础运行环境检查

回执与开关（带值的命令会修改设置）
  boss display detail --session SESSION   仅本会话记录详细执行事件和脱敏注入正文
  boss display summary --project 项目名   本机该项目的摘要观察；不修改项目仓库
  boss display off --session SESSION      关闭本会话新增观察，旧记录不会自动删除
  boss display inherit --session SESSION  恢复继承项目；默认 off
  boss events --session SESSION --detail  在终端展示已记录事件和实际注入正文
  boss events --session SESSION --follow --detail   持续显示新事件，Ctrl-C 退出
  boss receipt                  查看全局回执策略
  boss receipt always           全局：每轮提示
  boss receipt changes          全局：首次及识别结果变化时提示
  boss receipt off              全局：不显示回执，其他能力仍运行
  boss receipt --project 项目名  查看此项目覆盖值和实际策略（需要 v2）
  boss receipt always --project 项目名     仅此项目每轮提示
  boss receipt off --project 项目名        仅此项目不显示回执
  boss receipt inherit --project 项目名    恢复继承全局默认
  boss session mode SESSION     查看一个会话的模式
  boss session mode SESSION disabled       仅停用这个会话的 Hooks
  boss session mode SESSION observe-only   仅观察，不注入、不阻塞
  boss session mode SESSION enabled        恢复这个会话
  boss policy                   查看全局结束检查策略
  boss policy quiet             记录检查结果，不阻塞
  boss policy guarded           拦截未推送等数据丢失风险
  boss policy strict            同时检查连续性资料

初始化与任务（需明确授权写入）
  boss init --dry-run            预览，不写项目
  boss init --rules-only         配置全局规则，不初始化项目
  boss adopt /项目路径           接管一个仓库
  boss brain-init /项目路径      补齐已接管项目的 Brain
  boss session bind SESSION --task-id TASK-1 --project 项目名 --goal "目标"
                                默认只读关联，可重复 --project
  只有授权开发时才加 --access work；修正范围使用 --replace-projects。
  boss scan                     只读扫描候选；加 --adopt 才登记

知识、规范与交接
  boss knowledge list --session SESSION    查看知识待办
  boss help knowledge flag                如何登记已核实的知识
  boss help knowledge resolve             如何凭修改证据关闭待办
  boss wiki check /项目路径                 检查经验索引
  boss conventions check /项目路径          检查规范索引
  boss handoff check /项目路径              检查交接资料
  --fix 会修改索引；handoff check --run 会执行允许的验收命令。

机器恢复与维护（显式操作，不是查看帮助的副作用）
  boss help machine init         本地机器清单初始化
  boss help machine sync         同步清单；--push 涉及远程推送
  boss help machine restore      恢复机器清单；--clone 会克隆项目
  boss help machine timer-install 配置定时同步
  boss help vault-ref            只保存凭证名称与用途，不能写密钥值
  boss help migrate              旧数据迁移，先用 --dry-run
  boss help hook                 宿主内部入口，平时无需手动调用

回执显示在回答末尾，不是独立弹窗；关闭回执不等于关闭插件。
项目回执覆盖只保存在本机，对此项目的各会话生效，不随 Git 同步。
目前项目级控制只涉及回执，整个项目插件停用尚未实现。
同一会话可管理多个项目；识别到参考项目不代表允许修改它。
本帮助不覆盖 shell 自带的 help；终端请使用 boss help。
