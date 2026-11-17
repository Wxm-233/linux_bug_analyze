# 定位报告：CUR

当前版本（没有已知缺陷）上与众不同的簇：arm64 方向 23 簇，其中 13 簇有候选；riscv 方向 15 簇，其中 9 簇有候选；x86_64 方向 4 簇，其中 1 簇有候选

## riscv 与众不同：clock_gettime|EINVAL|EFAULT（3 个用例，例 1666：i:9 i:0）

- 没有静态来源

## riscv 与众不同：clock_gettime|EINVAL|arg2（3 个用例，例 881：i:9 t:0）

- 没有静态来源

## riscv 与众不同：fcntl|EFAULT|EINVAL（2 个用例，例 13747：f:eventfd i:11 i:2）

- **实现一致性检查**：f_getowner_uids（fs/fcntl.c:324），参数 [2] 的值与提示吻合；边界项 `put_user`，证据 2，得分 0.3784；静态取值 riscv=None、arm64=None、x86_64=None
- **实现一致性检查**：f_getowner_uids（fs/fcntl.c:325），参数 [2] 的值与提示吻合；边界项 `put_user`，证据 2，得分 0.3784；静态取值 riscv=None、arm64=None、x86_64=None

## riscv 与众不同：prctl|EFAULT|EINVAL（2 个用例，例 6695：i:28 i:1 i:1 i:0 i:40）

- **实现一致性检查**：__do_sys_prctl（kernel/sys.c:2565），参数 [1] 的值与提示吻合；边界项 `put_user`，证据 2，得分 0.5676；静态取值 riscv=None、arm64=None、x86_64=None
- **实现一致性检查**：__do_sys_prctl（kernel/sys.c:2703），参数 [1] 的值与提示吻合；边界项 `put_user`，证据 2，得分 0.5676；静态取值 riscv=None、arm64=None、x86_64=None
- **实现一致性检查**：get_unalign_ctl（arch/riscv/kernel/process.c:64），参数 [1] 的值与提示吻合；边界项 `put_user`，证据 2，得分 0.4541；静态取值 riscv=None、arm64=None、x86_64=None

## riscv 与众不同：prctl|EINVAL|EFAULT（4 个用例，例 4107：i:19 i:7 i:202 i:ffffffffffffffff i:ffffffffffffffff）

- **实现一致性检查**：prctl_get_tid_address（kernel/sys.c:2338），参数 [1] 的值与提示吻合；边界项 `put_user`，证据 2，得分 0.4541；静态取值 riscv=None、arm64=None、x86_64=None

## riscv 与众不同：raw_nr|ENOSYS|EFAULT（1 个用例，例 8495：i:8000000000000000 i:8000000000000000 i:7fffffff i:537ed3432644a858 i:3 i:2 i:8）

- **类型一致性检查**：系统调用号的检查；静态取值 riscv=0x1d9、arm64=0x1d9、x86_64=0x1d9

