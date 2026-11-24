# 判据：QEMU 动态验证 arm LPAE 迁移项页帧号截断（lpaeqemu_20261122，第六轮）

2026-11-22，Claude。用户：“QEMU 验证 arm LPAE”。对象是第五轮（`pfnswap_20261121`）的候选：arm LPAE（flatmem）上架构编码只保持 24 位页帧号，物理地址 ≥ 64GB 的页做迁移时，迁移项的页帧号会被截断。写于构建和运行之前。

## 一、要回答的问题

在 `df2908090cda` 的 arm LPAE 内核上，如果物理地址 64GB 以上确实有内存，并且这些页参与迁移，内核会不会出错？出错的样子是否与上游 `630dc25e43da` 修过的 x86 PAE 问题一致（迁移项清不掉、之后访问或读 pagemap 出错）？

## 二、环境

- 内核：`multi_v7_defconfig` + `ARM_LPAE` + `VMSPLIT_2G`（给 flatmem 的 `mem_map` 留出低端内存）+ `TRANSPARENT_HUGEPAGE` + `DEBUG_FS` + `DEBUG_VM`，内存模型保持默认（flatmem，与第五轮的 arm_lpae 变体一致）。构建目录在 WSL `/root/work/lpaeqemu/`，跑完只留 zImage、`.config`、`System.map`、日志。
- QEMU 8.2：`-M virt,highmem=on -cpu cortex-a15 -m 64G`，内存用稀疏文件作后端（`memory-backend-file`，只占实际写过的部分），跑完删除。
- 内核参数用 ARM 的 `mem=大小@起始` 指定两段内存：
  - **实验组**：`mem=1G@0x40000000 mem=512M@0x1000000000`（第二段在 64GB，页帧号 ≥ 2^24）；
  - **对照组**：`mem=1G@0x40000000 mem=512M@0x800000000`（第二段在 32GB，页帧号 < 2^24）。
  两组用同一个内核、同一个用户程序，只有第二段的地址不同。
- 用户程序（/init，clang 编译、不依赖 libc，直接发系统调用）：挂载 proc/sys/debugfs；把 THP 设为 always；映射 8MB 匿名内存、对齐到 2MB、`MADV_HUGEPAGE`、逐页写入可校验的内容；从 `/proc/self/pagemap` 读出物理页帧号并打印；向 `/sys/kernel/debug/split_huge_pages` 写入本进程和地址范围，强制拆分大页（拆分时内核用迁移项临时替换页表项，再换回来）；再读一次 pagemap；逐页校验内容；打印结果后关机。整个运行限时 300 秒。

## 三、判定

- **前提**：实验组拆分前读到的页帧号必须 ≥ 2^24（确实在 64GB 以上），而且拆分前是大页（pagemap 连续 512 页且对齐）；对照组页帧号 < 2^24。前提不成立就是“未能触发”，不下结论；允许调整一次（例如换触发方式为 `/proc/sys/vm/compact_memory`），调整写进 README。
- **确认**：前提成立，对照组拆分后 pagemap 正常、内容校验全部通过、没有内核报错；实验组出现以下任一：内核 oops/BUG/WARN（与迁移项、pagemap 或缺页相关）、进程卡住超时、拆分后 pagemap 仍显示交换类条目（迁移项残留）、内容校验不一致。
- **未确认**：前提成立，但两组表现相同（都正常）。这说明静态推断有误，或者有别的机制挡住了，要查清原因再写结论。
- 不管结果如何，这都只证明“内核在这种内存布局下会/不会出错”。现实中有没有 ARM LPAE 平台在 64GB 以上放内存，仍按第五轮的说法（目前没找到）。

## 四、其他

- 不改内核源码（只改配置）；不读封存材料；不调用模型；不对外报告。
- 统计行：模型调用 0；构建：arm LPAE 内核 1 个。
