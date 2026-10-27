# shmem历史XArray消费者的最小用户态探针

固定修复 `9fd154ba926b34c833b7bfc4c14ee2e931b3d743`，父版 `3390916aca7af1893ed2ebcdfee1d6fdb65bb058`。导出原 `lib/xarray.c` 和历史官方 `tools/testing/radix-tree` 适配；不修改 `/root/repos/linux`，不自行替换RCU或原WARN。

探针只调用 `xas_split_alloc()`，以 `XA_STATE_ORDER(..., new_order=0)` 构建真实操作状态，传入值条目而非512MB folio。记录原WARN的stderr、`xas_error()`、实际节点分配及清理计数。它验证真实消费者函数的用户态行为，不等同历史内核、实际folio拆分、ARM64指令或并发验证。

正常 `XA_CHUNK_SHIFT=6` 时，原消费者条件是 `xa_shift + 2 * XA_CHUNK_SHIFT < order`。new_order0的xa_shift为0，因此order13触发原WARN/`-ENOMEM`，order9不触发。`MAX_XAS_ORDER=11`是页缓存门禁保守上限，不能替代该消费者条件。order9/13及chunk6在准备期间仅为待本轮真实Kconfig与架构头认证的候选输入。

依赖：已有GCC/make，加标准 `liburcu-dev`；主智能体负责安装协调和真实架构参数来源。本目录没有自造RCU兼容层。

准备命令（WSL，所有输出在本目录）：

```sh
python3 prepare_consumer.py
cd source/tools/testing/radix-tree
make generated/map-shift.h generated/bit-length.h SHIFT=6
make -f Makefile -f ../../../../consumer_probe.mk consumer-probe SHIFT=6
./consumer-probe 9
./consumer-probe 13
```

以上构建沿用官方Makefile的ASan/UBSan和liburcu适配。order输入认证之后才将候选运行写成架构见证。初步工具核对没有运行原先人工常数的shmem函数probe。
