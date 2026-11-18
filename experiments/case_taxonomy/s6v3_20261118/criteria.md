# shmem 补丁 v3 的重测（判据，构建和运行之前定下）

2026-11-18，Claude。用户：“准备 v3 并重测”。来源：David Hildenbrand 审阅 v2 时建议，force 分支改为设好 `mask` 后 goto 到函数末尾，复用 `return THP_ORDERS_ALL_FILE_DEFAULT & mask;`。

- **修复变异 F6v3**（`tools/kbuild/mutations/s6v3.json`）：与 v3 补丁的代码完全一致（force 分支设 `mask` 并 `goto out;`，末尾加 `out:` 标签）。打在 7.3-rc2（df2908090cda）的 `pg64k` 档（arm64、64K 页）上。
- **复现程序**：沿用 `s6dyn_20261116/s6.c`（只读）；运行方式同 s6dyn（QEMU `-cpu cortex-a72`、4G、`-smp 2`）。运行脚本复制到本目录，只把输出目录改到这里；判定脚本也复制过来，逻辑不变。
- **格与预测**：

  | 格 | 内核 | 模式 | 预测 |
  |---|---|---|---|
  | v3_force | pg64k + F6v3 | force | **不复现**（有效运行中 0 次异常） |
  | plain_force | pg64k（原内核） | force | **复现**（对照，确认复现程序今天仍然有效） |

  每格 3 次。
- **判定**：沿用 s6dyn 判据第四节：有效运行中异常 ≥2 记“复现”，0 记“不复现”，其余记“不稳定”，有效运行少于 2 次记“无效”。两格的结论都与预测相符，v3 补丁说明里的 “With this change: 0/3” 才成立。
