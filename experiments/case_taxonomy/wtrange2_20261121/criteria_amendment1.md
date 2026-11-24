# 修订 1：盲审池排除已审条目，明确校准样本（wtrange2_20261121）

2026-11-21，Claude。写于本轮任何结果之前（allmodconfig 还在构建，本轮第 1 天的 12 条还没绑定）。门槛不变。

## 发现的问题

`evcard_20261121/cards.jsonl` 里的 `reviewed` 标记是在证据卡审查**之前**算的，所以证据卡那一轮审过的 9 条 WT，在 510 条里仍标为“未审”：
`get_loops_per_jiffy`、`set_f64_rd`、`pvclock_tsc_khz`、`build_device_resources`（sparc32）、`quick_pit_calibrate`、`flush_dcache_folio`（xtensa）、`amd_get_mmconfig_range`、`e820__reserve_resources`、`note_page`（riscv ptdump）。

## 改动

1. **盲审池**（第 4～5 天）再排除这 9 条（以 `evcard_20261121/review/items.json` 里的 WT 条目为准）。
2. **校准样本**明确为三部分：
   - 本轮第 1 天能绑定的条目；
   - 上一轮第 1 天能绑定的 4 条；
   - 上面 9 条中被某个窄目标构建覆盖的。
   这 9 条都有审查结论（8 条排除、1 条完整线索），用来检查“放得下”有没有错判：
   - 结论为“完整线索”的 AMD 必须不是“放得下”；
   - 排除原因是“值域放得下”的，静态判“可能超界”或“未知”不算错（只是没证出来）；
   - 排除原因不是值域的（已有守卫、32 位分支、有意截断、只用低位、实际不可达），静态判“放得下”时必须给出与源码一致的理由，否则算错误证明。
