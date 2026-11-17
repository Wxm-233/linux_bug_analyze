#include "k.h"

static spinlock_t Linit;

static int helper_user(void *p) { char b[4]; return (int)copy_from_user(b, p, 4); }
void do_trap_x(void *p) { helper_user(p); }
void do_trap_y(void *p) { (void)p; local_irq_enable(); msleep(1); }
void __init init_fn(void) { spin_lock(&Linit); msleep(1); spin_unlock(&Linit); }
