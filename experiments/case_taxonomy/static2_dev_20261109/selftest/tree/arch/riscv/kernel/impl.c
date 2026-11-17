#include <linux/ops.h>
#include <asm/lim.h>
int impl_op(int a) { if (arch_check(a)) return -EINVAL; return 0; }
int impl_op2(int a) { if (a == 7) return -EINVAL; return 0; }
struct ops riscv_ops = { .op = impl_op };
