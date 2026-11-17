# 统一报告：A171（修复前、修复后内核）

## 实现一致性（效果依赖）

（本树没有这类检查的数据）

## 类型一致性

动态确认 18、动态检查通过 0、转人工 0、动态发现但静态归因不对或没有静态来源 35。

### 动态确认

- 用例 15767：`recvfrom` i:2b i:fffffffffffff i:8000000000000000 i:2803 b:z:1 b:g:8184（a171_pre 返回 EBADF；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  - **类型一致性检查**：用户地址上限（相对上限提示值）；静态取值 riscv=0x7fffffffffffffff、arm64=0x10000000000000、x86_64=nonconst；探测 a171_pre: 指针检查上限 0x8000000000000000，可映射最高 0x100000000000000、a171_fix: 指针检查上限 0x100000000000001，可映射最高 0x100000000000000、a171_ref_arm64: 指针检查上限 0x10000000000001，可映射最高 0x10000000000000、a171_ref_x86_64: 指针检查上限 0xfffffffffff001，可映射最高 0xfffffffffff000；**同架构自洽问题**：a171_pre 两个上限对不上（第一候选）
- 用例 15778：`recvfrom` i:7 i:fffffffffffff i:10000000000001 i:0 i:a888 i:5（a171_pre 返回 EBADF；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  - **类型一致性检查**：用户地址上限（相对上限提示值）；静态取值 riscv=0x7fffffffffffffff、arm64=0x10000000000000、x86_64=nonconst；探测 a171_pre: 指针检查上限 0x8000000000000000，可映射最高 0x100000000000000、a171_fix: 指针检查上限 0x100000000000001，可映射最高 0x100000000000000、a171_ref_arm64: 指针检查上限 0x10000000000001，可映射最高 0x10000000000000、a171_ref_x86_64: 指针检查上限 0xfffffffffff001，可映射最高 0xfffffffffff000；**同架构自洽问题**：a171_pre 两个上限对不上（第一候选）
- 用例 15805：`recvfrom` f:signalfd i:8000000000000000 i:100000000 i:0 t:0 i:0（a171_pre 返回 ENOTSOCK；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  - **类型一致性检查**：用户地址上限（相对上限提示值）；静态取值 riscv=0x7fffffffffffffff、arm64=0x10000000000000、x86_64=nonconst；探测 a171_pre: 指针检查上限 0x8000000000000000，可映射最高 0x100000000000000、a171_fix: 指针检查上限 0x100000000000001，可映射最高 0x100000000000000、a171_ref_arm64: 指针检查上限 0x10000000000001，可映射最高 0x10000000000000、a171_ref_x86_64: 指针检查上限 0xfffffffffff001，可映射最高 0xfffffffffff000；**同架构自洽问题**：a171_pre 两个上限对不上（第一候选）
- 用例 15821：`recvfrom` f:dir i:fffffffffffff i:10 i:0 i:0 i:0（a171_pre 返回 ENOTSOCK；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  - **类型一致性检查**：用户地址上限（相对上限提示值）；静态取值 riscv=0x7fffffffffffffff、arm64=0x10000000000000、x86_64=nonconst；探测 a171_pre: 指针检查上限 0x8000000000000000，可映射最高 0x100000000000000、a171_fix: 指针检查上限 0x100000000000001，可映射最高 0x100000000000000、a171_ref_arm64: 指针检查上限 0x10000000000001，可映射最高 0x10000000000000、a171_ref_x86_64: 指针检查上限 0xfffffffffff001，可映射最高 0xfffffffffff000；**同架构自洽问题**：a171_pre 两个上限对不上（第一候选）
- 用例 15846：`recvfrom` f:eventfd o:g:62 i:fffffffffffff i:0 t:0 i:2（a171_pre 返回 ENOTSOCK；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  - **类型一致性检查**：用户地址上限（相对上限提示值）；静态取值 riscv=0x7fffffffffffffff、arm64=0x10000000000000、x86_64=nonconst；探测 a171_pre: 指针检查上限 0x8000000000000000，可映射最高 0x100000000000000、a171_fix: 指针检查上限 0x100000000000001，可映射最高 0x100000000000000、a171_ref_arm64: 指针检查上限 0x10000000000001，可映射最高 0x10000000000000、a171_ref_x86_64: 指针检查上限 0xfffffffffff001，可映射最高 0xfffffffffff000；**同架构自洽问题**：a171_pre 两个上限对不上（第一候选）
- 用例 15856：`ppoll` i:8000000000000000 i:0 b:z:0 i:0 i:8（a171_pre 返回 arg1；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  - **类型一致性检查**：用户地址上限（相对上限提示值）；静态取值 riscv=0x7fffffffffffffff、arm64=0x10000000000000、x86_64=nonconst；探测 a171_pre: 指针检查上限 0x8000000000000000，可映射最高 0x100000000000000、a171_fix: 指针检查上限 0x100000000000001，可映射最高 0x100000000000000、a171_ref_arm64: 指针检查上限 0x10000000000001，可映射最高 0x10000000000000、a171_ref_x86_64: 指针检查上限 0xfffffffffff001，可映射最高 0xfffffffffff000；**同架构自洽问题**：a171_pre 两个上限对不上（第一候选）
- 用例 15866：`recvfrom` f:signalfd i:7fffffffffffffff i:7fffffffffffffff i:800000 i:0 i:1（a171_pre 返回 ENOTSOCK；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  - **类型一致性检查**：用户地址上限（相对上限提示值）；静态取值 riscv=0x7fffffffffffffff、arm64=0x10000000000000、x86_64=nonconst；探测 a171_pre: 指针检查上限 0x8000000000000000，可映射最高 0x100000000000000、a171_fix: 指针检查上限 0x100000000000001，可映射最高 0x100000000000000、a171_ref_arm64: 指针检查上限 0x10000000000001，可映射最高 0x10000000000000、a171_ref_x86_64: 指针检查上限 0xfffffffffff001，可映射最高 0xfffffffffff000；**同架构自洽问题**：a171_pre 两个上限对不上（第一候选）
- 用例 15884：`recvfrom` f:pipewr i:8000000000000000 i:7ffffffffffffffe i:8 t:0 i:1（a171_pre 返回 ENOTSOCK；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  - **类型一致性检查**：用户地址上限（相对上限提示值）；静态取值 riscv=0x7fffffffffffffff、arm64=0x10000000000000、x86_64=nonconst；探测 a171_pre: 指针检查上限 0x8000000000000000，可映射最高 0x100000000000000、a171_fix: 指针检查上限 0x100000000000001，可映射最高 0x100000000000000、a171_ref_arm64: 指针检查上限 0x10000000000001，可映射最高 0x10000000000000、a171_ref_x86_64: 指针检查上限 0xfffffffffff001，可映射最高 0xfffffffffff000；**同架构自洽问题**：a171_pre 两个上限对不上（第一候选）
- ……另有 10 条，见 unified.json

### 动态检查通过

（已有数据没有逐条记录“检查了但没差异”的项）
（无）

### 转人工

（无）

### 动态发现但静态归因不对或没有静态来源

- 用例 350：`recvfrom` i:40d i:468d3e8195844fd6 i:8 i:3c b:g:1 i:2（a171_pre 返回 EBADF；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  静态归因不对：第一候选 **实现一致性检查**：move_addr_to_user（net/socket.c:300），参数 [5] 的值与提示吻合；边界项 `__put_user`，证据 2，得分 0.5253；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 1281：`sendto` f:udp i:5c4b7b79a6e1813e i:8 i:0 b:z:1 i:40（a171_pre 返回 EINVAL；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  没有静态来源
- 用例 3400：`listmount` b:a:1 i:1c242ff49989fa55 i:dc19 i:0（a171_pre 返回 E2BIG；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  没有静态来源
- 用例 4509：`sendto` f:neg i:aee6e91beb2f45e i:40 i:55a8e489 t:0 i:2000（a171_pre 返回 EBADF；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  没有静态来源
- 用例 5410：`sendto` f:ustream i:3d3ce47b5f837ebf i:ffffffffffffffff i:f84d8a2e b:g:8184 i:1000（a171_pre 返回 EINVAL；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  没有静态来源
- 用例 5656：`sendto` i:ffffff8d i:16d2fce67b42625e i:6dba i:ffffffff t:0 i:2000（a171_pre 返回 EBADF；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  没有静态来源
- 用例 6979：`recvfrom` f:ustream i:10ac45bf02b072a0 i:100000000 i:ffffffff i:73eefcb77a1b9a9c b:a:0（a171_pre 返回 EINVAL；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  静态归因不对：第一候选 **实现一致性检查**：put_cmsg（net/core/scm.c:255），参数 [3] 的值与提示吻合；边界项 `unsafe_put_user`，证据 2，得分 0.1201；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 7242：`listmount` b:a:0 i:27b615807ac3c17b i:1000 i:0（a171_pre 返回 E2BIG；a171_fix 返回 EFAULT；a171_ref_arm64 返回 EFAULT；a171_ref_x86_64 返回 EFAULT）
  没有静态来源
- ……另有 27 条，见 unified.json

## 调用上下文

（本树没有这类检查的数据）

