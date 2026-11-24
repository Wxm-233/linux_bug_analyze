# 判据修订 2：父版本法的编译命令再加一条强制包含（ecrecall_20261122）

2026-11-22，Claude。写于父版本法第一次运行失败之后、任何父版本法召回结果之前。

第一次在 `018e9828eb52` 的父版本 `d4e58d2c21d9`（v7.1）上运行：变体 20/20 生成成功，但所有构建的试编译都失败，规律 0 条（`logs/engine_d4e58d2c21d9.log`）。原因是头文件顺序：这个版本的 `include/linux/swapops.h` 用到 `SWP_MIGRATION_*`、`SWP_PTE_MARKER`，它们定义在 `include/linux/swap.h`，而 swapops.h 依赖调用者先包含 swap.h；引擎固定的求值头（mm.h、pgtable.h、swapops.h、leafops.h）没有包含它（df2908090cda 上 swapops.h 已自行处理这个依赖，所以前几轮没出问题）。

改动（只改编译命令，判定规则不变）：父版本法的所有版本、所有构建，在编译命令末尾加 `-include <该版本源码>/include/linux/swap.h`（与修订 1.2 的替身头文件同一处理方式）。回注法不受影响。
