## 四、当前进度

**2026-11-07（GPT）停点：`boundary_audit_20261107` 的三个问题分析完成；修订工具和小规模验证完成，三架构全量重合并未运行，下一步由Claude执行。当前结果不能承诺三类检查不漏报。**

### 已完成

1. **三类检查定义**（`experiments/case_taxonomy/boundary_taxonomy_20261106/`）：135条跨架构样本中，检查一数据一致性37条、检查二实现完备性57条、检查三调用上下文26条，构建与工具链15条排除。三类保持不变；这只是分类归属，不能代替静态覆盖证明。
2. **构建矩阵**（`/root/work/boundary_build/`）：riscv RV64、arm64、x86_64的defconfig均成功；编译数据库分别4231、10898、3093条。内核固定 `df2908090cda368b01ff43709f51890076c56157`（v7.3-rc2），源码只读。编译数据库条目包含汇编和少量宿主工具，不等于C单元数。
3. **原边界枚举三架构均完成**（`experiments/case_taxonomy/boundary_enum_20261106/`）：

   | 架构 | 成功C单元 | 失败 | 边界符号 | 边界点 |
   |---|---:|---:|---:|---:|
   | riscv | 4185 | 0 | 3610 | 198841 |
   | arm64 | 10822 | 0 | 6399 | 443423 |
   | x86_64 | 3022 | 0 | 7428 | 243747 |

   共有符号1712；历史120条按原口径命中20条，非空functions为20/84，空字段36条。旧19点自测、同名静态对象键与分阶段合并自测通过；旧 `selftest/failure.txt` 是历史记录。旧产物保留，不能用本轮发现倒改其数字。
4. **边界审计**（`experiments/case_taxonomy/boundary_audit_20261107/`）：判据先冻结，SHA256=`a2a23f31e0c7e7509c2e940751fda9f361f3cf18c2348be12376b1bdc6a87ba2`。入口为本轮 `README.md`、`stats.json`、`sample_miss_analysis.json`、`unresolved_analysis.json`、`generated_analysis.json`，逐条索引 `sample_review.md`。
   - **问题1完成**：100条未命中逐补丁核查。64条非空主因a22/b9/c3/d0/e30；36条空字段a10/b2/c8/d2/e14；合计a32/b11/c11/d2/e44，u0。a=配置/架构输入不覆盖，b=历史位置/名字失效，c=边界定义/语义域缺口，d=实际跨层关系被漏，e=提取/匹配问题。check1/2/3未命中32/45/23。空字段27条与某补丁文件相交、15条与某恢复符号相交，但不代表修复行/配置覆盖；A105是符号存在而KASAN分支不活动的例子。历史查全率仍null。
   - **问题2完成**：按4层各4单元抽样，重现的definition_not_found逐单元16/16对上，共30141处；另按固定种子细查400处。内建11723、前向不完整类型10489、编译期/优化守卫6742、活动架构汇编632、链接脚本272、dummy声明130、未活动公共C127、非core公共模块定义14、模块alias6、未完全恢复static-call4、未活动架构C1、未构建架构汇编1。632次汇编引用中562次跨层（150个去重源位置）、70次层内。562/30141=1.86457%只适用于所选引用下界，全riscv比例/数量null；局部变量、参数、普通字段已被采集器过滤，三者在此失败样本中均0。
   - **问题3完成**：生成使用位置贡献riscv241符号/601点、arm64264/613、x86_64419/794。生成syscall表分别227/375、252/383、407/604，应保留；模块元数据8/14、6/16、0/0，候选主池之外单列但原始池保留；其他运行生成代码保留。不能整体排除或把所有@build归架构。宿主scripts/tools单元也需单列。
   - **实证漏项**：A058嵌套vmemmap宏；B446公共强实现与公共弱桩同USR，旧解析器只处理公共弱→架构强，漏了riscv syscall表引用；另有C→架构汇编（如bitmap.h的memcpy）被C定义解析漏掉。直接跨层点仍缺宏/传递实现、回调/描述表、配置、链接脚本、属性和隐含ABI/内存模型。
   - **本轮修订工具**：`criteria_amendment2.md` 已冻结SHA256=`5dd78f17b7f532e4dc06affe4661ff500419f1de1304e4fd3925b40778ee9c54`。`repair_policy.py`、`remerge.py` 修复任意层别的公共强弱绑定，补C→汇编的独立对象证据，保留原始AST表并另出运行时候选池；不改旧enumerate.py和旧结果。原19点/12符号预期不变且通过；新回归1个AST点、2个C→asm点（1跨层）通过；真实B446的2个引用和1个bitmap→memcpy小范围缓存重放通过；检查点恢复也通过。
   - **不可变性与统计**：旧目录97文件逐个SHA256一致，`verification.json`通过。模型接口0，内核构建0，全量扫描0，全量重合并0；两套小夹具做了独立编译链接。新确认内核缺陷0，新内核疑点0。工具漏项不计作内核缺陷。

### 下一步：Claude前台分批重合并

**分工（用户11-07确定）**：机械批量构建、扫描、合并、既定汇总由Claude在WSL执行；分析、设计和新工具交给Codex（GPT）。GPT不要自己运行全量扫描/重合并；小规模自测与几个单元验证可以做。此次也遵守这一分工。

1. 先读本轮README、criteria及两个amendment。不要重扫或重建内核，也不要运行旧summarize/report覆盖产物。对各架构重复相应命令，直到打印complete且输出目录有complete.txt：

   ```powershell
   wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/claude_remerge_batch.sh riscv 128
   wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/claude_remerge_batch.sh arm64 128
   wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/claude_remerge_batch.sh x86_64 128
   ```

   每架构首次建立定义/链接索引，之后每次128个C单元；名义总调用次数34/86/25。前台运行，不用nohup或&。初始化仍读取全部现有缓存与对象表，耗时未测；中断后同命令续跑。新检查点和产物只写本轮 `revised/<arch>/<摘要>/`，绝不能写旧目录。
2. 三个架构都完成后：

   ```powershell
   wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/boundary_audit_20261107/run.sh report_revised.py
   ```

   输出本轮 `revised_stats.json`；核对C单元4185/10822/3022、失败0、输入与工具摘要一致，B446 compat系统调用表引用存在。分别报告AST表、运行时池、C→汇编独立证据及未解析数，不直接把不同证据点数相加。新历史命中率适配未实现，仍null；宏漏项A058不会由本次重合并自动修复。该全三架构汇总尚未真实运行，只在小夹具验证了汇总辅助逻辑。
3. 每架构/阶段完成后追加进度日志并更新这里。重合并运行或新结果若揭示设计矛盾，按规则记录后交用户决定，不为数字改预期。

### 尚未完成与之后的顺序

1. 完成上述重合并及数字核验；不能因为局部修订自测通过就改成“不漏报”。4处static-call生成声明真实绑定未恢复，全riscv漏项比例/数量仍null。
2. 另写判据后设计宏依赖、保守回调/描述表与内部实现闭包，补链接脚本、配置/Kconfig、函数/段属性、隐含字宽/对齐/内存模型。矩阵按样本相关开关规划RV32、BPF_JIT、KEXEC、KPROBES、THP等；此次没有生成或构建新配置。
3. 再依据边界规模、系统调用可达性和可观察后果决定提示/目标点位策略，实现三类检查，优先已有CTX与副作用/返回值/输入检查基础。
4. 在120条修复前版本评估查全率、当前版本抽样误报，之后接定向差分模糊测试；这些均未做。LoongArch及汇报文档仍按后续授权推进，不改旧轮或用户论文/周报。

---

