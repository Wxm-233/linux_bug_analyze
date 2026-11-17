#include <linux/ops.h>
#include <asm/lim.h>
extern struct ops riscv_ops;
static struct ops *g_ops = &riscv_ops;
static int l6(int v)
{
	if (arch_check(v))
		return -EINVAL;
	if (v == ARCH_LIM + 1)
		return -EINVAL;
	return 0;
}
static int l5(int v) { return l6(v); }
static int l4(int v) { return l5(v); }
static int l3(int v) { return l4(v); }
static int l2(int v) { return l3(v); }
static int l1(int v) { return l2(v); }
void setup(struct ops *o) { o->op2 = impl_op2; }
long __do_sys_demo(int x, int y)
{
	struct ops tmp = (struct ops){ .op2 = impl_op2 };
	l1(x);
	return g_ops->op(y) + tmp.op2(y);
}
