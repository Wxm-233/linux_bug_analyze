# N2.13 CFG 探查执行材料独立复核（2026-10-19）

只读最终计划、两版 `raw/<profile>/attempt.json`、`result.json`、四种输出及保存的目标区段/绑定；未再执行编译器，也未扩大旧构建树检查。两次尝试均绑定最终计划 SHA-256 `851acc456df0298f7ef7c55c5c928c5cf38e291518db810a13f4207a99c2b059`，每版 `attempt` 仅登记一次，实际 `argv` 与计划逐项相同。顺序为 s390 先成功、随后 x86；s390 39.679 秒、x86 33.815 秒，均 exit 0、`CFG_record_available`。两版各六个受保护旧文件的 `protected_after` 与计划 `protected_before` 逐项相同；这只验证选定六项，并非全旧构建树封存。

四种计划输出（assembly、original、gimple、cfg）均位于新 stage 的各自 `raw` 子目录且存在；逐文件重算 SHA-256 与结果记录一致。独立以 CFG dump 原始字节按绑定的半开区间切出 record、再按 record 内区间切出函数体：两版 full dump、record、body 摘要均与绑定一致，保存的 portable `*.consumer.cfg.txt` 字节摘要也恰等于对应 record。s390 record 为 15,740 字节、266 行，x86 为 16,765 字节、275 行；每段各有一个目标 `;; Function sched_core_cpu_starting (` 头、22 个 `<bb N> :` 块标记及 22 条 `;; N succs { … }` 记录。首尾位于目标函数记录内，源行注解仍可见。s390 stderr 1518 字节，系 `pgtable.h` 的 tautological-compare 警告；x86 stderr 空，二者 stdout 均空，警告没有被删改为成功证据。

本轮证实相同已读父版输入/配置可产生保存完整的编译器 CFG 取证材料，并通过固定输出/旧文件身份门槛。`succs` 是编译器正常图的候选转移，不自动证明真/假极性、实际运行可达、call/asm 必返回、对象别名或公共接口要求。后续必须按真实块/显式目标建立有界解析与跨 IR 唯一绑定；不能由 22 块/22 行统计或旧 GIMPLE E 编号直接声称三段条件机制已自动闭合。两版是同一已读案例的两配置，不是两个新缺陷或独立验证样本。
