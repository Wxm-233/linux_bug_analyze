# 判据修订 1：变异要同时定义 `__HAVE_ARCH_MOVE_PTE`（r4_20261115）

2026-11-15 14:45，Claude。写于第一批阳性运行之后、重建变异内核之前。

## 发现

- 通用代码 `include/linux/pgtable.h` 第 1473～1475 行是：

  ```c
  #ifndef __HAVE_ARCH_MOVE_PTE
  #define move_pte(pte, old_addr, new_addr)	(pte)
  #endif
  ```

  保护条件不是判据第三节以为的“架构没有定义 `move_pte`”。sparc 自带的实现是同时定义 `__HAVE_ARCH_MOVE_PTE` 和 `move_pte`。
- 第一批变异只定义了 `move_pte`：
  - x86_64：`-Werror` 下报“`move_pte` macro redefined”，R4a、R4b 构建失败，6 次阳性运行没有内核可启动；
  - riscv：只报警告，后面的通用定义覆盖了变异，所以变异实际没生效。riscv 阳性运行中 P1、P2 都是 0/3，符合“变异无效”的预期。
- 所以第一批阳性运行全部无效，移到 `runs/pos_invalid1/`，判错结果改名为 `judge_pos_invalid1.*`。阴性对照和覆盖两组不涉及变异，结果有效，保留。

## 修订

1. 变异定义改为两行，和 sparc 的做法一样：

   ```c
   #define __HAVE_ARCH_MOVE_PTE
   #define move_pte(...) ...
   ```

   `move_pte` 的内容与判据第三节相同。`mutate.py` 照此修改。
2. 重建 4 个变异内核（R4a、R4b × riscv、x86_64），重跑阳性组（每个 3 次）。基线、配置和其余流程不变。
3. 构建日志保留每个变异内核里“macro redefined”出现的次数，应当为 0。

其余不变。
