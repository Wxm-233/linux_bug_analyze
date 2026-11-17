#ifndef GEN_H
#define GEN_H
#include <asm/arch.h>
#ifndef ARCH_HAS_HOOK
/* generic fallback: a constant stub */
static inline int arch_hook(void) { return 0; }
#endif
#endif
