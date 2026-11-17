#include <linux/task.h>
#include <asm/m2.h>
void use_m2(struct task *t) { arch_multi(t); }
