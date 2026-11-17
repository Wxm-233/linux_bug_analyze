# 统一报告：A310（修复前、修复后内核）

## 实现一致性（效果依赖）

（本树没有这类检查的数据）

## 类型一致性

动态确认 26、动态检查通过 0、转人工 0、动态发现但静态归因不对或没有静态来源 0。

### 动态确认

- 用例 2522：`raw_nr` i:ffffffffffffffff i:2463a388e60ef978 i:25 i:7fffffff i:7fffffffffffffff i:1000 i:1000（a310_pre 返回 arg0；a310_fix 返回 ENOSYS；a310_ref_arm64 返回 ENOSYS；a310_ref_x86_64 返回 ENOSYS）
  - **类型一致性检查**：系统调用号的检查；静态取值 riscv=0x1cf、arm64=0x1cf、x86_64=0x1cf（第一候选）
- 用例 2900：`raw_nr` i:ffffffffffffffff i:8000000000000000 i:7fffffff i:100 i:1 i:ffffffff i:100（a310_pre 返回 neg；a310_fix 返回 ENOSYS；a310_ref_arm64 返回 ENOSYS；a310_ref_x86_64 返回 ENOSYS）
  - **类型一致性检查**：系统调用号的检查；静态取值 riscv=0x1cf、arm64=0x1cf、x86_64=0x1cf（第一候选）
- 用例 3821：`raw_nr` i:ffffffffffffffff i:80000000 i:2 i:ffffffffffffffff i:100 i:10 i:ffffffff（a310_pre 返回 arg0；a310_fix 返回 ENOSYS；a310_ref_arm64 返回 ENOSYS；a310_ref_x86_64 返回 ENOSYS）
  - **类型一致性检查**：系统调用号的检查；静态取值 riscv=0x1cf、arm64=0x1cf、x86_64=0x1cf（第一候选）
- 用例 6020：`raw_nr` i:ffffffffffffffff i:ffffffffffffffff i:ffffffffffffffff i:ffff i:719137941a8eb531 i:8000000000000000 i:ff（a310_pre 返回 EPERM；a310_fix 返回 ENOSYS；a310_ref_arm64 返回 ENOSYS；a310_ref_x86_64 返回 ENOSYS）
  - **类型一致性检查**：系统调用号的检查；静态取值 riscv=0x1cf、arm64=0x1cf、x86_64=0x1cf（第一候选）
- 用例 7578：`raw_nr` i:ffffffffffffffff i:ff i:1000 i:ff i:2 i:40 i:7fffffff（a310_pre 返回 arg0；a310_fix 返回 ENOSYS；a310_ref_arm64 返回 ENOSYS；a310_ref_x86_64 返回 ENOSYS）
  - **类型一致性检查**：系统调用号的检查；静态取值 riscv=0x1cf、arm64=0x1cf、x86_64=0x1cf（第一候选）
- 用例 8295：`raw_nr` i:ffffffffffffffff i:100 i:100 i:100 i:ffffffff i:12 i:10000（a310_pre 返回 arg0；a310_fix 返回 ENOSYS；a310_ref_arm64 返回 ENOSYS；a310_ref_x86_64 返回 ENOSYS）
  - **类型一致性检查**：系统调用号的检查；静态取值 riscv=0x1cf、arm64=0x1cf、x86_64=0x1cf（第一候选）
- 用例 9074：`raw_nr` i:ffffffffffffffff i:7fffffff i:7fffffffffffffff i:8000000000000000 i:80000000 i:8000000000000000 i:8707c6f1e89c19ce（a310_pre 返回 arg0；a310_fix 返回 ENOSYS；a310_ref_arm64 返回 ENOSYS；a310_ref_x86_64 返回 ENOSYS）
  - **类型一致性检查**：系统调用号的检查；静态取值 riscv=0x1cf、arm64=0x1cf、x86_64=0x1cf（第一候选）
- 用例 9112：`raw_nr` i:ffffffffffffffff i:0 i:0 i:0 i:0 i:0 i:0（a310_pre 返回 arg0；a310_fix 返回 ENOSYS；a310_ref_arm64 返回 ENOSYS；a310_ref_x86_64 返回 ENOSYS）
  - **类型一致性检查**：系统调用号的检查；静态取值 riscv=0x1cf、arm64=0x1cf、x86_64=0x1cf（第一候选）
- ……另有 18 条，见 unified.json

### 动态检查通过

（已有数据没有逐条记录“检查了但没差异”的项）
（无）

### 转人工

（无）

### 动态发现但静态归因不对或没有静态来源

（无）

## 调用上下文

（本树没有这类检查的数据）

