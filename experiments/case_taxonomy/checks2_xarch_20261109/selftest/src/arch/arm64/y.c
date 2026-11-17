#include <linux/task.h>
#include <linux/common.h>
void arch_set_state(struct task *t) { t->flags = 5; }
void arch_flush(void) { log_only(3); }
void arch_reset2(void) { common_reset(); }
