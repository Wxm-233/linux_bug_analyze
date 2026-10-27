# book/drawer 提取器 v2：已读案例开发记录

本轮仅用此前已解封的 Linux 提交 `f1045056c726440469d89d23c13734bcd6c0d15b` 及其父版开发和检查提取器。它们**不是未读验证集**；原先冻结的 v1 运行和选样文件保持原样，参见 [`next_stage_review.md`](next_stage_review.md)。结果可用 [`topology_v2_f104_development.py`](topology_v2_f104_development.py) 重跑，逐条事实与源码行号保存在 [`topology_v2_f104_development.json`](topology_v2_f104_development.json)。

v2 为 book/drawer 单独识别两个有边界的源码形状：

1. 父版：`drivers/base/topology.c` 的 show/read、二进制属性数组和 ID 属性数组均由 `CONFIG_SCHED_BOOK` 或 `CONFIG_SCHED_DRAWER` 门控；属性名是 `book_siblings{,_list}` / `drawer_siblings{,_list}`，读取函数仍调用 `topology_*_cpumask`。这个版本的公共头文件尚无对应默认 ID/掩码宏。对于 s390，只有显式给出 `CONFIG_SCHED_TOPOLOGY` 值，且在该版 `arch/s390/Kconfig` 中找到其选择对应 `SCHED_*` 的关系时，才推导旧守卫。x86 的判断限制在该版的 s390 定义与 x86 Kconfig 未选中这一源码形状。
2. 修复版：`include/linux/topology.h` 在 fallback 前以原生 `topology_*_id` **且** `topology_*_cpumask` 定义出 `TOPOLOGY_*_SYSFS`；驱动的三处出口都用该宏。提取器核对双宏条件、提供者、回退边界、读取函数、属性名及三个注册入口。配对条件、Kconfig 关系或命名不是已识别形状时返回 `insufficient`。

固定 SMP 与 sysfs 构建为开启，组合父版/修复版、book/drawer、s390 的 `SCHED_TOPOLOGY=on/off/unknown` 和 x86 的未指定配置，共 **16 条条件记录**。12 条为 `normal`，4 条为 `insufficient`（均为 s390 配置未知）；没有 `hit`。s390 配置开启时原生 ID/掩码及属性同时存在；关闭时同时不存在。x86 在所查版本中没有该家族原生提供者，也未导出旧属性；新版双宏门控同样不导出。由此只支持“该开发案例在这些条件下没有发现导出与原生提供者不配对”，并不构成 12 个独立缺陷样本或准确率估计。单元测试另外注入“旧守卫仍导出但掩码提供者缺失”，应为 `hit`；同一缺失在新版双宏守卫下应为 `normal`（不导出）。

接口语义仍以对应历史版本的源码提供者/消费者与文档作暂定依据，不能凭“当时只有 s390 使用”永久禁止其他架构提供它。当前脚本只覆盖这两个家族的 s390/x86 静态源码形状，不能完整求解 Kconfig、C 预处理、动态可见性、真实 sysfs 行为或硬件拓扑；其他架构以及陌生守卫形状会拒判。下一轮应冻结 v2 代码与评估规则，再在未参与开发的修订上测试范围与误报，不能用本开发矩阵充当独立验证。
