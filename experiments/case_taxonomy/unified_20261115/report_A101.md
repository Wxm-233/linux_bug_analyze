# 统一报告：A101（修复前、修复后内核）

## 实现一致性（效果依赖）

（本树没有这类检查的数据）

## 类型一致性

动态确认 0、动态检查通过 0、转人工 0、动态发现但静态归因不对或没有静态来源 9。

### 动态确认

（无）

### 动态检查通过

（已有数据没有逐条记录“检查了但没差异”的项）
（无）

### 转人工

（无）

### 动态发现但静态归因不对或没有静态来源

- 用例 2594：`mmap` i:40000000 i:100000000 i:fffffffffffffff4 i:0 i:2 i:80000000（a101_pre 返回 ENOMEM；a101_fix 返回 EINVAL；a101_ref_arm64 返回 EINVAL；a101_ref_x86_64 返回 EINVAL）
  静态归因不对：第一候选 **不归类**：try_grab_folio（mm/gup.c:144），参数 [3, 4] 的值与提示吻合；边界项 `WARN_ON_ONCE`，证据 1，得分 0.0513；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 6832：`mmap` i:ffffffffffffff7b i:1000 i:1 i:3 f:perfsw i:0（a101_pre 返回 ENOMEM；a101_fix 返回 big；a101_ref_arm64 返回 big；a101_ref_x86_64 返回 big）
  静态归因不对：第一候选 **不归类**：try_grab_folio（mm/gup.c:144），参数 [2, 3, 5] 的值与提示吻合；边界项 `WARN_ON_ONCE`，证据 1，得分 0.0513；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 6961：`mmap` i:ffffffffffffffef i:1000 i:1 i:3 f:ustream i:0（a101_pre 返回 ENOMEM；a101_fix 返回 ENODEV；a101_ref_arm64 返回 ENODEV；a101_ref_x86_64 返回 ENODEV）
  静态归因不对：第一候选 **不归类**：try_grab_folio（mm/gup.c:144），参数 [2, 3, 5] 的值与提示吻合；边界项 `WARN_ON_ONCE`，证据 1，得分 0.0513；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 7046：`mmap` i:ffffffffffffffff i:1 i:ffffffffffffffe1 i:80000000 f:dir i:0（a101_pre 返回 ENOMEM；a101_fix 返回 EINVAL；a101_ref_arm64 返回 EINVAL；a101_ref_x86_64 返回 EINVAL）
  静态归因不对：第一候选 **不归类**：try_grab_folio（mm/gup.c:144），参数 [0, 1, 5] 的值与提示吻合；边界项 `WARN_ON_ONCE`，证据 1，得分 0.0513；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 7771：`mmap` i:40000000 i:1000 i:1 i:3 f:perfsw i:0（a101_pre 返回 ENOMEM；a101_fix 返回 big；a101_ref_arm64 返回 big；a101_ref_x86_64 返回 big）
  静态归因不对：第一候选 **不归类**：try_grab_folio（mm/gup.c:144），参数 [2, 3, 5] 的值与提示吻合；边界项 `WARN_ON_ONCE`，证据 1，得分 0.0513；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 11776：`mmap` i:fffffffffffffff0 i:1000 i:1 i:3 f:perfsw i:0（a101_pre 返回 ENOMEM；a101_fix 返回 big；a101_ref_arm64 返回 big；a101_ref_x86_64 返回 big）
  静态归因不对：第一候选 **不归类**：try_grab_folio（mm/gup.c:144），参数 [2, 3, 5] 的值与提示吻合；边界项 `WARN_ON_ONCE`，证据 1，得分 0.0513；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 12704：`mmap` i:40000000 i:1000 i:1 i:40 f:perfsw i:0（a101_pre 返回 ENOMEM；a101_fix 返回 EINVAL；a101_ref_arm64 返回 EINVAL；a101_ref_x86_64 返回 EINVAL）
  静态归因不对：第一候选 **实现一致性检查**：rb_alloc_aux（kernel/events/ring_buffer.c:748），参数 [3] 的值与提示吻合；边界项 `virt_to_page`，证据 2，得分 0.1934；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 14728：`mmap` i:ffffffffffffffef i:1000 i:1 i:3 f:perfsw i:0（a101_pre 返回 ENOMEM；a101_fix 返回 big；a101_ref_arm64 返回 big；a101_ref_x86_64 返回 big）
  静态归因不对：第一候选 **不归类**：try_grab_folio（mm/gup.c:144），参数 [2, 3, 5] 的值与提示吻合；边界项 `WARN_ON_ONCE`，证据 1，得分 0.0513；静态取值 riscv=None、arm64=None、x86_64=None
- ……另有 1 条，见 unified.json

## 调用上下文

（本树没有这类检查的数据）

