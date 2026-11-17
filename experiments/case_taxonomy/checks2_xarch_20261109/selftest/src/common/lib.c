#include <linux/common.h>
#include <linux/gen.h>
int g_mask;
int g_r;
void cpumask_clear_all(void) { g_mask = 0; }
void log_only(int v) { (void)v; }
void common_reset(void) { g_r = 0; }
int common_alloc(int size, int flags) { return size + flags; }
int common_use_hook(void) { return arch_hook(); }
