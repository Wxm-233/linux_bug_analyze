# P3 LoongArch PMU/SMP 顺序：源码解封前冻结协议

2026-09-28。仅依据固定 500 清单的 SHA/标题、Git 日期与改动路径，事前选定 `f3334ebb8a2a1841c2824594dd992e66de19deb2` 与父版 `d3119bc985fb645ad3b2a9cf9952c1d56d9daaa3`。选样记录 `state_pmu_selection_pre.json` SHA-256 为 `1c383d66948a985ece5a62d64270f7f955ade0fe7a6698ffa139304294fc5613`；固定清单 SHA-256 为 `8e61c456af84b1cee027a38793e4146a5d96bf652307fc83582e4c661f4d995a`。此时**未读目标修复正文、补丁或父/修复源码**。

冻结 `state_pmu_probe.py` SHA-256 为 `4dcccc5674e47952048b5baa732405cbe2657b834e4f536231ac8bfc217b4b2f`（`python -m py_compile` 通过）。输入**单一历史修订源码**，不读提交正文、差分或另一修订。范围仅 `arch/loongarch/kernel/perf_event.c`、同目录 Makefile、`init/main.c`；适用条件是 LoongArch `CONFIG_PERF_EVENTS=y` 且静态 Kbuild 形状可辨。它从源码自动定位唯一 initcall 函数、函数内直接 `for_each_online_cpu`/`cpu_online_mask`/相关 SMP 读取和启动期 `do_pre_smp_initcalls → smp_init → do_basic_setup` 顺序。旧版如在 pre-SMP initcall 内直接读取 online CPU，则输出 `hit` 候选；修复版同一直接消费若在 post-SMP 则输出 `normal`；`CONFIG_PERF_EVENTS=n` 只在构建条件可证时输出 `not_applicable`。找不到直接首次消费者、构建链或启动顺序则为 `insufficient`。`perf_pmu_register`/CPUHP 注册只能作间接线索，**不能**升级为已证 `hit`。

这条规则的 P 是源码中 `smp_init()` 完成的阶段条件；C 必须是 PMU initcall 函数**直接**读取 online CPU 状态。标题仅帮助选择了一个有希望的主题，不向检查器提供符号或补丁信息。若真实链经过间接调用，本轮应如实拒判，后续可以用它开发下一版，但已解封样本不能再算新版的独立留出。修复版是同一提交的匹配正常对照，不是独立正常提交；`CONFIG_PERF_EVENTS=n` 是不适用对照，不可充当已运行正常。任何 `hit` 只是源码顺序复核点，不证明真实故障或跨架构泛化。

运行次序：①固定脚本对父版 `CONFIG_PERF_EVENTS=y`、修复版 `y` 和父版 `n` 各输出原始 JSON；②在读取补丁前记录三份原始输出 SHA 和脚本 SHA；③再解封补丁/源码作人工因果复核。每个状态必须保留 `hit/normal/not_applicable/insufficient/runner_error` 原义。最多这一条候选，不临时换样；不调用付费模型、不修改 topology v3、不计新缺陷分母。
