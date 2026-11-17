#include <linux/task.h>
#include <linux/common.h>
#include <linux/gen.h>
int g_x;
int arch_hook(void) { return g_x; }
void arch_set_state(struct task *t) { t->state = 2; }
void arch_flush(void) { cpumask_clear_all(); }
int arch_alloc(void) { return common_alloc(4096, 8); }
int arch_map_event(int e) { if (e < 0) return -95; return e; }
static int regs[32];
int arch_get_reg(int idx) { if (idx >= 32) return 0; return regs[idx]; }
void arch_dir(void) { }
void arch_private(void) { log_only(2); }
int not_candidate(void) { return g_x; }
void arch_multi(struct task *t) { t->state = 3; }
