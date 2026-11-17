# 统一报告：A181（修复前、修复后内核）

## 实现一致性（效果依赖）

（本树没有这类检查的数据）

## 类型一致性

动态确认 2、动态检查通过 0、转人工 0、动态发现但静态归因不对或没有静态来源 1。

### 动态确认

- 用例 12705：`recvmsg` f:udgram t:0 i:4（a181_pre 返回 val；a181_fix 返回 val；a181_ref_arm64 返回 val；a181_ref_x86_64 返回 val）
  - **实现一致性检查**：scm_detach_fds（net/core/scm.c:385），参数 [2] 的值与提示吻合；边界项 `put_user`，证据 2，得分 0.0953；静态取值 riscv=None、arm64=None、x86_64=None（第一候选）
- 用例 15097：`recvmsg` f:udgram t:0 i:0（a181_pre 返回 val；a181_fix 返回 val；a181_ref_arm64 返回 val；a181_ref_x86_64 返回 val）
  - **实现一致性检查**：____sys_recvmsg（net/socket.c:2836），参数 [2] 的值与提示吻合；边界项 `__put_user`，证据 2，得分 0.4503；静态取值 riscv=None、arm64=None、x86_64=None（第一候选）

### 动态检查通过

（已有数据没有逐条记录“检查了但没差异”的项）
（无）

### 转人工

（无）

### 动态发现但静态归因不对或没有静态来源

- 用例 14531：`recvmsg` f:udgram t:0 i:88（a181_pre 返回 val；a181_fix 返回 val；a181_ref_arm64 返回 val；a181_ref_x86_64 返回 val）
  没有静态来源

## 调用上下文

（本树没有这类检查的数据）

