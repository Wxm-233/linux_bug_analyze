/* Minimal stand-ins for the kernel primitives the checker recognises by name. */
typedef struct { int x; } raw_spinlock_t;
typedef struct { raw_spinlock_t rlock; } spinlock_t;
struct mutex { int x; };
#define __init __attribute__((section(".init.text")))
#define GFP_KERNEL 1
#define GFP_ATOMIC 2
void __might_sleep(const char *f, int l);
static inline int gfpflags_allow_blocking(int g) { return g == GFP_KERNEL; }
static inline void might_alloc(int g) { if (gfpflags_allow_blocking(g)) __might_sleep("x", 1); }
void *__kmalloc(unsigned long s, int g);
static inline void *kmalloc(unsigned long s, int g) { might_alloc(g); return __kmalloc(s, g); }
static inline unsigned long arch_local_irq_save(void) { return 0; }
static inline void arch_local_irq_restore(unsigned long f) { (void)f; }
static inline void arch_local_irq_enable(void) { }
#define local_irq_save(f) do { f = arch_local_irq_save(); } while (0)
#define local_irq_restore(f) arch_local_irq_restore(f)
#define local_irq_enable() arch_local_irq_enable()
void _raw_spin_lock(raw_spinlock_t *l);
void _raw_spin_unlock(raw_spinlock_t *l);
unsigned long _raw_spin_lock_irqsave(raw_spinlock_t *l);
void _raw_spin_unlock_irqrestore(raw_spinlock_t *l, unsigned long f);
static inline raw_spinlock_t *spinlock_check(spinlock_t *l) { return &l->rlock; }
static inline void spin_lock(spinlock_t *l) { _raw_spin_lock(&l->rlock); }
static inline void spin_unlock(spinlock_t *l) { _raw_spin_unlock(&l->rlock); }
#define spin_lock_irqsave(l, f) do { f = _raw_spin_lock_irqsave(spinlock_check(l)); } while (0)
static inline void spin_unlock_irqrestore(spinlock_t *l, unsigned long f) { _raw_spin_unlock_irqrestore(&l->rlock, f); }
#define raw_spin_lock(l) _raw_spin_lock(l)
#define raw_spin_unlock(l) _raw_spin_unlock(l)
void mutex_lock(struct mutex *m);
void mutex_unlock(struct mutex *m);
void msleep(unsigned int ms);
unsigned long copy_from_user(void *to, const void *from, unsigned long n);
void on_each_cpu(void (*fn)(void *), void *info, int wait);
