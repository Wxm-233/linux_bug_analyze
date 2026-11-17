#include "k.h"

static spinlock_t L;
static raw_spinlock_t R;
static struct mutex M;

void s_local(void) { spin_lock(&L); mutex_lock(&M); spin_unlock(&L); }
void s_branch(int c) { if (c) spin_lock(&L); mutex_lock(&M); if (c) spin_unlock(&L); }
void s_loop_ok(int n) { for (int i = 0; i < n; i++) { spin_lock(&L); spin_unlock(&L); } msleep(1); }
void s_goto(int e)
{
	spin_lock(&L);
	if (e)
		goto out;
	msleep(1);
out:
	spin_unlock(&L);
	msleep(2);
}
static void takes_spin(void) { spin_lock(&L); spin_unlock(&L); }
void r_raw(void) { raw_spin_lock(&R); takes_spin(); raw_spin_unlock(&R); }
static void cb(void *p) { (void)p; mutex_lock(&M); mutex_unlock(&M); }
void i_irq(void) { unsigned long f; local_irq_save(f); on_each_cpu(cb, 0, 1); local_irq_restore(f); }
void alloc(void)
{
	spin_lock(&L);
	kmalloc(8, GFP_ATOMIC);
	kmalloc(8, GFP_KERNEL);
	spin_unlock(&L);
}
void nested_ok(void) { unsigned long f; spin_lock_irqsave(&L, f); takes_spin(); spin_unlock_irqrestore(&L, f); }
void sw(int x)
{
	switch (x) {
	case 1:
		spin_lock(&L);
		break;
	case 2:
		msleep(1);
		break;
	}
	msleep(3);
}
