#ifndef FX_WRAP_H
#define FX_WRAP_H
#include <asm/fx.h>
static inline int fx_wrap(int p) { return fx_arch_get(p); }
#endif
