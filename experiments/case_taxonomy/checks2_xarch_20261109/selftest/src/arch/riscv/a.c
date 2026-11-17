#include <linux/task.h>
#include <linux/common.h>
#include <asm/m1.h>
static void rv_helper(struct task *t) { t->flags = 1; }
void arch_set_state(struct task *t) { rv_helper(t); }
void arch_flush(void) { log_only(1); }
static void rv_do_reset(void) { common_reset(); }
void arch_reset2(void) { rv_do_reset(); }
int arch_alloc(void) { return common_alloc(4096, 0); }
int arch_map_event(int e) { if (e < 0) return -2; return e + 1; }
static int regs[32];
int arch_get_reg(int idx) { return regs[idx]; }
void arch_dir(void) { common_reset(); }
static void arch_private(void) { }
int not_candidate(void) { return 0; }
void use_private(void) { arch_private(); }
void use_m1(struct task *t) { arch_multi(t); }
