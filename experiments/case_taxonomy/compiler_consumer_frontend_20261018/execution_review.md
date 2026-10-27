# N2.11 真实编译器输出独立复核（2026-10-18）

## old_s390

本次只读核对已批准计划 SHA-256 `fb174a23f1126e899099839d503af7148f62678e681a0e6b5ec4d9f8c07ce6af` 与脚本 SHA-256 `cc62b5b01b890164ebf1d7b84b4060dd5dba0b34ac97c853828bf8a8dbcf565e`，执行记录中的 argv/cwd 与计划完全一致。目标 GCC 一次编译退出 0，耗时 33.477 秒；汇编、original 和 gimple dump 三个计划输出均存在并有摘要。标准输出为空，1518 字节诊断保存在 stderr；诊断是 `pgtable.h` 中比较恒真的编译器警告，参数未因警告改动。本审查没有再次运行编译。

计划中的 6 个旧文件（原 `.i`、`.config`、`.core.o.cmd`、`core.c`、旧 `.d` 和 `.o`）与执行后的路径/存在性/摘要逐项一致。`raw/old_s390` 记录的所有新文件均在本阶段目录；这是列明文件的有限检查，并非全文件系统写入证明。

目标 GIMPLE dump SHA-256 `ec6cdd49254152c5e66d1b74a6f10b7f0f15d094d41d06c5a0d154ea5cc5103a`，提取片段字节范围 `[2504549, 2521761)`、30381–30602 行；重算片段摘要与 `consumer.extract.json` 一致，且与保存的 `consumer.gimple.txt` 字节相同。片段首行精确为 `void sched_core_cpu_starting (unsigned int cpu)`，前一函数已以 `}` 结束并隔空行，片段末尾为目标闭合 `}`，随后才是 `sched_rq_cpu_starting`；因此本次没有触发正则可能跨行多吞上一标识符行的理论风险。这个有限边界核对仅支持“完整目标 GCC 片段可定位”，不证明其中字段读写、数据流、别名、架构合同或实际运行路径。

## old_x86 与交付绑定

old_s390 已满足登记的第二 profile 门槛后，old_x86 按同一批准计划一次执行，退出 0，耗时 26.494 秒，stderr 为空。实际 argv/cwd 与计划逐项相同，计划/脚本 SHA 保持不变；汇编、original、gimple 三个新输出均存在。6 个旧路径（其中旧依赖文件原本不存在）的执行后存在性和摘要与计划一致，没有把不存在文件误报为被保留的实体。

x86 GIMPLE dump SHA-256 `a3ccc06b08f65f2d32bc6eb8e12d3d1c35f590239ddedfdc47c5b679afb7567f`；提取 `[2254687, 2272918)`、27130–27360 行共 231 行，片段 SHA-256 `b5c042e3f6e9f0b649e65a306dc58274e131f06e2b9861109ab2a784a51b536c`。独立按 dump 字节切片后，与原 `consumer.gimple.txt` 一致。其首行同样精确为 `void sched_core_cpu_starting (unsigned int cpu)`，前一函数已闭合，最后是目标 `}`，其后才出现 `sched_rq_cpu_starting`；本次 x86 也未触发提取正则跨行多吞的风险。

两份交付到 stage 顶层的 `old_s390.consumer.gimple.txt`、`old_x86.consumer.gimple.txt` 均与相应 raw 片段逐字节相同；各 `consumer_binding.json`、`results_summary.json` 所记片段、原提取记录及 raw result 摘要均重算一致。由此可说**同一既知父版公共消费者在两个已保存配置上，目标 GCC 的完整函数表示可取得**。这只是前端可行性与来源绑定，不是两个独立缺陷、运行差异、已证明字段集合、自动数据流/别名分析或跨架构契约判断。尤其 `tentative_line_inventory` 对路径中的点号和汇编段名有污染，不能将其词法命中直接统计为结构字段读写。
